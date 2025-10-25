# aicoding

本项目提供一个用于统计系统监控覆盖情况的命令行工具，帮助快速找出不同业务系统的必需监控项覆盖率与缺失情况。

## 使用方法

1. 准备监控数据文件，支持 JSON 或 CSV 格式。可参考 `data/monitoring_sample.json` 的结构：
   - `system`：系统名称。
   - `component`：可选，子模块或组件名称。
   - `monitor`：监控项名称。
   - `required`：是否为必需监控项。
   - `monitored`：该监控是否已覆盖。

2. 运行报表生成脚本：

```bash
python monitoring_report.py --input data/monitoring_sample.json
```

默认会在终端输出表格形式的覆盖情况。可通过以下参数定制输出：

- `--format`：在终端展示 `table`（默认）、`markdown`、`csv` 或 `json`。
- `--output`：将结果写入文件，当前支持 `.csv` 与 `.md/.markdown`。

示例：

```bash
python monitoring_report.py --input data/monitoring_sample.json --format markdown
python monitoring_report.py --input data/monitoring_sample.json --output report.md
```

输出示例（表格模式）：

```
系统 | 必需监控项 | 已覆盖 | 覆盖率 | 可选监控项 | 可选已覆盖 | 缺失必需监控
----...（省略）
```

生成的报表还会给出整体系统数量、必需监控覆盖率等指标，便于快速评估监控体系的完整性。
