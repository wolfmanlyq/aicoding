"""Generate coverage report for system monitoring.

This script reads monitoring configuration records from a JSON or CSV file
and produces coverage statistics for each system along with an overall summary.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def bool_from_value(value: object) -> bool:
    """Convert various string representations to boolean.

    Accepts truthy strings ("true", "yes", "1", "y") and falsy strings
    ("false", "no", "0", "n"). Case insensitive. Non-string values are
    coerced using ``bool``.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "y", "1", "on", "enabled"}:
            return True
        if normalized in {"false", "no", "n", "0", "off", "disabled"}:
            return False
    return bool(value)


@dataclass
class MonitoringRecord:
    """Single monitoring configuration record."""

    system: str
    monitor: str
    component: Optional[str]
    required: bool
    monitored: bool
    importance: Optional[str] = None
    notes: Optional[str] = None

    @classmethod
    def from_mapping(cls, mapping: Dict[str, object]) -> "MonitoringRecord":
        try:
            system = str(mapping["system"]).strip()
            monitor = str(mapping.get("monitor") or mapping.get("metric") or "").strip()
        except KeyError as exc:  # pragma: no cover - defensive branch
            raise ValueError(f"Missing mandatory field: {exc.args[0]}") from exc

        if not system:
            raise ValueError("Field 'system' must not be empty")
        if not monitor:
            raise ValueError("Field 'monitor' must not be empty")

        component_raw = mapping.get("component") or mapping.get("module")
        component = str(component_raw).strip() if component_raw is not None else None
        required = bool_from_value(mapping.get("required", True))
        monitored = bool_from_value(
            mapping.get("monitored", mapping.get("covered", mapping.get("active", False)))
        )
        importance_raw = mapping.get("importance") or mapping.get("criticality")
        importance = str(importance_raw).strip() if importance_raw is not None else None
        notes_raw = mapping.get("notes") or mapping.get("comment")
        notes = str(notes_raw).strip() if notes_raw is not None else None
        return cls(system, monitor, component, required, monitored, importance, notes)


def load_records(input_path: Path) -> List[MonitoringRecord]:
    """Load monitoring records from a JSON or CSV file."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix == ".json":
        content = json.loads(input_path.read_text(encoding="utf-8"))
        if isinstance(content, dict) and "records" in content:
            raw_records = content["records"]
        else:
            raw_records = content
        if not isinstance(raw_records, Sequence):
            raise ValueError("JSON input must be a list of records or have a 'records' key")
        return [MonitoringRecord.from_mapping(record) for record in raw_records]

    if suffix == ".csv":
        with input_path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            return [MonitoringRecord.from_mapping(row) for row in reader]

    raise ValueError("Unsupported file type. Use JSON or CSV.")


@dataclass
class SystemCoverage:
    system: str
    required_total: int
    required_covered: int
    optional_total: int
    optional_covered: int
    missing_monitors: List[MonitoringRecord]

    @property
    def coverage_ratio(self) -> Optional[float]:
        if self.required_total == 0:
            return None
        return self.required_covered / self.required_total


@dataclass
class CoverageSummary:
    systems: int
    required_total: int
    required_covered: int
    optional_total: int
    optional_covered: int

    @property
    def average_coverage(self) -> Optional[float]:
        if self.systems == 0:
            return None
        return self.required_covered / self.required_total if self.required_total else None


def analyze(records: Iterable[MonitoringRecord]) -> Tuple[List[SystemCoverage], CoverageSummary]:
    systems: Dict[str, List[MonitoringRecord]] = {}
    for record in records:
        systems.setdefault(record.system, []).append(record)

    system_coverages: List[SystemCoverage] = []
    total_required = total_required_covered = 0
    total_optional = total_optional_covered = 0

    for system, system_records in sorted(systems.items()):
        required_records = [r for r in system_records if r.required]
        optional_records = [r for r in system_records if not r.required]
        required_total = len(required_records)
        required_covered = sum(1 for r in required_records if r.monitored)
        optional_total = len(optional_records)
        optional_covered = sum(1 for r in optional_records if r.monitored)
        missing = [r for r in required_records if not r.monitored]

        total_required += required_total
        total_required_covered += required_covered
        total_optional += optional_total
        total_optional_covered += optional_covered

        system_coverages.append(
            SystemCoverage(
                system=system,
                required_total=required_total,
                required_covered=required_covered,
                optional_total=optional_total,
                optional_covered=optional_covered,
                missing_monitors=missing,
            )
        )

    summary = CoverageSummary(
        systems=len(system_coverages),
        required_total=total_required,
        required_covered=total_required_covered,
        optional_total=total_optional,
        optional_covered=total_optional_covered,
    )
    return system_coverages, summary


def format_percentage(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def render_table(system_coverages: Sequence[SystemCoverage], summary: CoverageSummary) -> str:
    headers = [
        "系统",
        "必需监控项",
        "已覆盖",
        "覆盖率",
        "可选监控项",
        "可选已覆盖",
        "缺失必需监控",
    ]
    rows: List[List[str]] = []
    for item in system_coverages:
        missing_desc = ", ".join(r.monitor for r in item.missing_monitors) or "-"
        rows.append(
            [
                item.system,
                str(item.required_total),
                str(item.required_covered),
                format_percentage(item.coverage_ratio),
                str(item.optional_total),
                str(item.optional_covered),
                missing_desc,
            ]
        )

    headers_line = " | ".join(headers)
    divider = "-+-".join("-" * len(h) for h in headers)
    body_lines = [" | ".join(row) for row in rows]

    summary_lines = [
        "总览:",
        f"  系统数量: {summary.systems}",
        f"  必需监控项: {summary.required_covered}/{summary.required_total} ({format_percentage(summary.average_coverage)})",
        f"  可选监控项: {summary.optional_covered}/{summary.optional_total}",
    ]

    return "\n".join([headers_line, divider, *body_lines, "", *summary_lines])


def write_csv(
    system_coverages: Sequence[SystemCoverage], summary: CoverageSummary, output_path: Path
) -> None:
    fieldnames = [
        "system",
        "required_total",
        "required_covered",
        "coverage_ratio",
        "optional_total",
        "optional_covered",
        "missing_monitors",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for item in system_coverages:
            writer.writerow(
                {
                    "system": item.system,
                    "required_total": item.required_total,
                    "required_covered": item.required_covered,
                    "coverage_ratio": f"{item.coverage_ratio:.4f}" if item.coverage_ratio is not None else "",
                    "optional_total": item.optional_total,
                    "optional_covered": item.optional_covered,
                    "missing_monitors": "; ".join(r.monitor for r in item.missing_monitors),
                }
            )
        writer.writerow({})
        writer.writerow(
            {
                "system": "SUMMARY",
                "required_total": summary.required_total,
                "required_covered": summary.required_covered,
                "coverage_ratio": f"{summary.average_coverage:.4f}" if summary.average_coverage else "",
                "optional_total": summary.optional_total,
                "optional_covered": summary.optional_covered,
            }
        )


def write_markdown(system_coverages: Sequence[SystemCoverage], summary: CoverageSummary) -> str:
    headers = ["系统", "必需监控项", "已覆盖", "覆盖率", "可选监控项", "可选已覆盖", "缺失必需监控"]
    header_line = " | ".join(headers)
    separator = " | ".join([":-" for _ in headers])
    rows = []
    for item in system_coverages:
        missing_desc = ", ".join(r.monitor for r in item.missing_monitors) or "-"
        rows.append(
            " | ".join(
                [
                    item.system,
                    str(item.required_total),
                    str(item.required_covered),
                    format_percentage(item.coverage_ratio),
                    str(item.optional_total),
                    str(item.optional_covered),
                    missing_desc,
                ]
            )
        )
    summary_text = (
        f"**总览**: {summary.systems} 个系统，必需监控覆盖率 {format_percentage(summary.average_coverage)}, "
        f"可选监控 {summary.optional_covered}/{summary.optional_total}."
    )
    return "\n".join([header_line, separator, *rows, "", summary_text])


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="统计系统监控覆盖情况")
    parser.add_argument("--input", "-i", type=Path, required=True, help="输入数据文件（JSON 或 CSV）")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="将报表写入文件（支持 CSV 或 Markdown，根据扩展名自动判断）",
    )
    parser.add_argument(
        "--format",
        choices=["table", "markdown", "csv", "json"],
        default="table",
        help="不输出到文件时，命令行展示的格式",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    records = load_records(args.input)
    system_coverages, summary = analyze(records)

    if args.output:
        suffix = args.output.suffix.lower()
        if suffix == ".csv":
            write_csv(system_coverages, summary, args.output)
        elif suffix in {".md", ".markdown"}:
            args.output.write_text(write_markdown(system_coverages, summary), encoding="utf-8")
        else:
            raise ValueError("Unsupported output format. Use .csv or .md/.markdown")
        print(f"报表已写入 {args.output}")
        return 0

    if args.format == "table":
        print(render_table(system_coverages, summary))
    elif args.format == "markdown":
        print(write_markdown(system_coverages, summary))
    elif args.format == "csv":
        temp_path = Path("-temp-report.csv")
        write_csv(system_coverages, summary, temp_path)
        print(temp_path.read_text(encoding="utf-8"))
        temp_path.unlink(missing_ok=True)
    elif args.format == "json":
        payload = {
            "systems": [
                {
                    "system": item.system,
                    "required_total": item.required_total,
                    "required_covered": item.required_covered,
                    "coverage_ratio": item.coverage_ratio,
                    "optional_total": item.optional_total,
                    "optional_covered": item.optional_covered,
                    "missing_monitors": [r.monitor for r in item.missing_monitors],
                }
                for item in system_coverages
            ],
            "summary": {
                "systems": summary.systems,
                "required_total": summary.required_total,
                "required_covered": summary.required_covered,
                "average_coverage": summary.average_coverage,
                "optional_total": summary.optional_total,
                "optional_covered": summary.optional_covered,
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
