# Swag Labs 成功登录测试

使用 optics-framework 的 CSV 用例，覆盖 Web、Android 和 iOS 的成功登录场景。

每个平台执行相同流程：启动应用 → 验证登录表单 → 输入 `standard_user` / `secret_sauce` → 点击登录 → 验证商品列表和 `Sauce Labs Backpack` 可见 → 关闭应用。账号为 Swag Labs 公开演示账号。

| 平台 | 目标 | 驱动 |
| --- | --- | --- |
| Web | https://www.saucedemo.com | Playwright / Chromium |
| Android | Swag Labs Mobile App (`com.swaglabsmobileapp`) | Appium / UiAutomator2 |
| iOS | Swag Labs Mobile App (`com.saucelabs.SwagLabsMobileApp`) | Appium / XCUITest |

各平台目录包含：

- `test_cases/test_cases.csv`：Suite Setup、成功登录用例、Suite Teardown。
- `modules/modules.csv`：启动、表单检查、输入、登录、结果断言、关闭步骤。
- `test_data/elements.csv`：平台元素定位器、公开演示账号，以及 Web 站点地址。
- `config.yaml`：驱动、设备及元素识别配置。
- `execution_output/`：运行后生成的日志、截图和 JUnit 报告。

## 运行

在本项目根目录执行：

```bash
./run-tests web
./run-tests android
./run-tests ios
```

入口优先使用当前 Python 环境中的 optics-framework，否则使用 `~/.optics/venv/bin/python`。也可通过 `OPTICS_PYTHON=/path/to/python ./run-tests web` 指定解释器。每个平台在自己的目录运行，避免并行执行时写入同一份相对路径日志。

Web 需要安装 Playwright Chromium。移动端需要预先安装 Swag Labs Mobile App，并分别在两个终端启动 Appium 服务：

```bash
# 终端 1：Android
appium --address 127.0.0.1 --port 4723

# 终端 2：iOS
appium --address 127.0.0.1 --port 4725

# 终端 3：并行执行两端；任一端失败，命令返回非零退出码
./run-tests mobile
```

Android 配置对应本机已连接的 `TECNO BF6`，iOS 配置对应本机的 `iPhone 15 Pro / iOS 17.5` 模拟器。更换设备时，请修改各自 `config.yaml` 中的 `deviceName`、`udid` 和适用的 `platformVersion`。Appium 需安装对应的 `uiautomator2` / `xcuitest` 驱动。

移动端定位器针对英文界面，使用应用的 accessibility ID；商品名称断言使用各平台的原生 XPath。启动时强制重新启动应用，结束时终止应用；`noReset: true` 保留已安装应用的数据。

配置只保留启用的驱动、设备、元素来源、并行通信端口和文件日志，以及 Web 窗口与减速设置。已去掉未启用的 OCR、图像识别、LLM、自愈配置、空字段及重复默认值。移动端的 `noReset`、`forceAppLaunch`、`shouldTerminateApp` 使用 optics-framework 1.11.0 的默认值 `true`。当前不使用 MJPEG 视频流，因此未配置其端口。页面源码与截图来源仍用于定位回退和执行诊断，予以保留。

## Web 窗口与执行节奏

本项目使用 optics-framework 1.11.0。该版本的 Playwright 驱动没有将 `slow_mo` 传给 Playwright，也没有实现最大化窗口配置。

`scripts/optics_runner.py` 在当前进程内扩展浏览器启动方法：传入 `slow_mo`，关闭固定 viewport，并通过 Chromium CDP 最大化窗口（包括 macOS）。其余 CSV 读取、动作、断言和报告仍由 optics 执行，不修改全局安装包。Web 用例只启动一次浏览器，结果显示 2 秒后关闭。

请通过 `./run-tests web` 执行。直接运行 `optics execute web` 仍能运行用例，但不会应用本项目的窗口最大化和减速适配。执行速度在 `web/config.yaml` 的 `slow_mo` 中调整（毫秒），结果展示时间在 `web/modules/modules.csv` 的关闭步骤中调整。

## CI

已配置三份 GitHub Actions 工作流：`.github/workflows/optics-web.yml`、`optics-android.yml`、`optics-ios.yml`。提交到 GitHub 后，在推送到 `main` / `master`、创建或更新 PR 时运行，也支持在 Actions 页面手动触发。

Web 使用 Ubuntu 无界面 Chromium；Android 使用 Ubuntu 的 Android 14 模拟器；iOS 使用 `macos-15-intel`、Xcode 16.4 和 iOS 18.5 模拟器。三端独立运行，不需要本机设备在线。

工作流先做 `dry_run` 校验，再执行测试、发布 JUnit 报告和保存压缩后的日志截图。CI 通过 `ci/prepare_suite.py` 在临时目录生成配置副本，不修改本机配置。依赖安装、iOS 模拟器应用要求及故障排查见 [CI 说明](ci/README.md)。

## 数据

官方将 `elements.csv` 定义为变量存储，表头为 `Element_Name,Element_ID`，通过 `${变量名}` 在步骤中引用；它不只存放定位器，也可以存放文本等输入值。框架按文件内容识别数据类型，不要求另外创建账号或设置文件。参见 [官方 elements.csv 说明](https://mozarkai.github.io/optics-framework/user_workflow/#elementscsv)。

三端已统一将定位器和公开演示账号放回 `elements.csv`，Web 地址也在同一文件中；同一平台内变量名保持唯一。这里的账号是公开演示数据，不应将真实账号凭据提交到仓库。

## 并行端口

| 平台 | Appium URL | 驱动通信端口 |
| --- | --- | --- |
| Android | `http://127.0.0.1:4723` | `systemPort: 8200` |
| iOS | `http://127.0.0.1:4725` | `wdaLocalPort: 8100` |

同一个 Appium 服务也支持多个会话，URL 相同本身并不禁止 Android/iOS 并行。这里使用独立服务便于查看日志和分别重启，同时明确设备 UDID 与驱动端口。以后增加同平台设备时，每个并行会话也需要独立的设备和相关端口；多个 iOS 构建还需考虑独立 `derivedDataPath`。参见 [Appium 并行测试说明](https://appium.github.io/appium-xcuitest-driver/7.35/guides/parallel-tests/)。

`.gitignore` 已排除各级 `logs/`、`execution_output/`、系统文件、Python 缓存及本地环境文件。忽略规则不会自动移除 Git 已经跟踪的文件。

移动端应用来源：[Sauce Labs 官方示例应用](https://github.com/saucelabs/sample-app-mobile)。
