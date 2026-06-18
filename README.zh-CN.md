# Self-Healing Code RPA Framework

一个将网页自动化流程封装成可运行、可测试、可修复、可回滚 Skill 的自愈型 Code RPA 框架。

当前版本是 `v0.1.0`。它聚焦于 Web RPA、Python + Playwright、YAML Skill、自愈修复闭环和版本回滚。

## 核心理念

传统 RPA 通常是：

```text
脚本
  -> 运行
  -> 页面变化
  -> 失败
  -> 人工修复
```

本框架的目标是：

```text
Skill
  -> Runtime
  -> 失败捕获
  -> repair_request.json
  -> patch.json
  -> sandbox
  -> version
  -> rollback
```

正常执行时不调用 LLM。只有当流程失败时，框架才生成结构化修复上下文，并允许经过严格校验的选择器级补丁进入沙箱测试和版本化流程。

## 当前能力边界

已支持：

- Web RPA
- Python + Playwright 运行时
- 基于 YAML 的 Skill 定义
- 主选择器与备用选择器解析
- 步骤级执行日志
- 失败现场快照捕获
- `repair_request.json` 生成
- 选择器级 `patch.json` 校验
- 沙箱补丁测试
- Skill 版本化
- 回滚到历史版本
- CLI、Skill Generator、Skill Validator、Skill SDK、Version CLI

暂不支持：

- OCR
- Desktop RPA
- 调度系统
- Web UI
- 多租户
- 云端运行
- 数据库重构
- 真实网站集成
- 正常执行期间的 LLM 调用
- 由 AI 自动自由改写代码

## 安装

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m playwright install chromium
```

安装后可以使用：

```powershell
code-rpa --version
```

也可以直接通过模块入口运行：

```powershell
python -m code_rpa --version
```

## 运行 Demo Skill

```powershell
code-rpa --project-root . skill run web_report_export
```

当前内置示例 Skill：

```text
example_skills/
  web_report_export/
```

它使用本地 HTML fixture 模拟登录、进入报表页面、选择日期范围、导出报表并验证成功状态。

## 常用命令

```powershell
code-rpa --project-root . skill list
code-rpa --project-root . skill show web_report_export
code-rpa --project-root . skill validate web_report_export
code-rpa --project-root . skill create invoice_export
code-rpa --project-root . skill test web_report_export
```

版本命令：

```powershell
code-rpa --project-root . version list web_report_export
code-rpa --project-root . version current web_report_export
code-rpa --project-root . version show web_report_export <version_id>
code-rpa --project-root . version rollback web_report_export <version_id>
```

补丁校验：

```powershell
code-rpa --project-root . repair validate path\to\repair_request.json path\to\patch.json
```

## Skill SDK

```python
from code_rpa.sdk import SkillBuilder

skill = SkillBuilder("invoice_export")
skill.add_step(
    id="open_invoice_page",
    type="navigate",
    goal="Open the invoice export page.",
    url="about:blank",
)
skill.add_step(
    id="click_export",
    type="click",
    goal="Click the export button.",
    selector_ref="export_button",
    target_description="Button that starts invoice export.",
)
skill.add_selector(
    "export_button",
    primary="#export-invoices",
    fallbacks=["button[data-testid='export-invoices']"],
)
skill.save()
```

SDK 只负责生成标准 Skill 文件，不改变 Runtime，不调用 LLM，也不扩展 RPA 能力边界。

## 测试

```powershell
python -m pytest
```

当前基线：

```text
27 passed
```

## 架构模块

- `rpa_runtime/`: 执行 Skill，管理浏览器操作、步骤执行、选择器解析、日志和失败观测。
- `skill_registry/`: 加载 Skill，管理 Skill 版本，创建修复快照，并支持回滚。
- `repair_agent/`: 生成修复请求，校验补丁，运行沙箱测试，并控制修复流水线。
- `code_rpa/`: CLI、Skill Validator、Skill SDK 等工程化入口。
- `example_skills/`: 示例 Skill。
- `tests/`: 单元测试、补丁流水线测试和 Chromium 集成测试。

## 安全边界

- 正常执行不得调用 LLM。
- Phase 3 当前只允许选择器级修复。
- `patch.json` 不得修改 Runtime、Repair Agent、Registry 或任意 Python 代码。
- `code_changes` 必须为 `null`。
- 高风险步骤需要人工确认。
- 密码、token、cookie、session 数据不得写入日志或修复请求。

## 当前定位

这是一个实验性框架项目，不是生产级 RPA SaaS。当前重点是将自愈型 Code RPA 的核心闭环固化为可安装、可运行、可测试、可持续开发的 GitHub 框架。

下一阶段最有价值的方向不是扩展 Runtime，而是补充 2 到 3 个真实业务 Skill 示例，让框架从 Demo 走向可落地参考。
