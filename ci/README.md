# GitHub Actions CI

依据 [Optics 官方 CI 文档](https://optics-framework.org/docs/run/ci) 配置。官方页面提供 Web 和 Android 示例；本项目依据 Appium 的 XCUITest 要求补充了 iOS 模拟器工作流。

| 工作流 | Runner | 测试环境 |
| --- | --- | --- |
| `.github/workflows/optics-web.yml` | `ubuntu-24.04` | Playwright Chromium，headless |
| `.github/workflows/optics-android.yml` | `ubuntu-24.04` | KVM、Android API 34、x86_64、UiAutomator2 |
| `.github/workflows/optics-ios.yml` | `macos-15-intel` | Xcode 16.4、iPhone 16 / iOS 18.5、XCUITest |

三份工作流相互独立，可以并行运行。触发条件为推送到 `main` / `master`、PR 和 `workflow_dispatch`。其他默认分支名称需要修改工作流中的 `push.branches`。

## 使用

将整个项目（包括 `.github/`、`ci/` 和三端用例目录）提交到 GitHub 仓库并启用 Actions。在 Actions 页面可分别选择 **Optics Web**、**Optics Android**、**Optics iOS** 手动运行；手动运行入口需先将工作流放到默认分支。

公开演示账号和应用下载不需要额外 secrets。工作流使用 GitHub 自动提供的 token 发布检查，不发送 PR 评论。来自 fork 或 Dependabot 的 PR 使用仅注释/Job Summary 模式，避免依赖 Checks 写权限。

## 执行流程

1. Linux 上的 `validate` job 安装对应 Optics 引擎，运行 CI 配置生成器的回归检查和 `optics dry_run`。
2. `test` job 在自己的 runner 上安装浏览器或 Appium，准备模拟器，下载并校验移动应用。
3. `prepare_suite.py` 复制测试用例、模块和数据，在 `$RUNNER_TEMP` 创建全新目录，并替换本机设备信息。移动端临时模块在关闭应用前增加截图和页面树采集；Android 首次等待用户名框的预算改为 120 秒（Optics 1.11.0 会在原生定位与 OCR 间分配预算，原生定位实际最多约 60 秒），其余断言保持 30 秒。已存在的目标目录会被拒绝，避免旧报告混入；本地用例不变。
4. Web 直接运行无界面浏览器；移动端先安装应用，再启动 Appium，并轮询 `/status` 的 `ready` 字段，服务就绪后才执行测试。
5. 发布 JUnit 并上传 `.tgz` 归档（保留 14 天）。报告含失败、解析失败或没有测试均使 job 失败。Optics 本身返回非零退出码也会使执行步骤失败。

iOS 在运行用例前通过 `ci/build_wda.sh` 单独编译当前固定 XCUITest 驱动附带的 WebDriverAgent，构建步骤最多 15 分钟。Appium 使用相同 `derivedDataPath` 和 `usePrebuiltWDA: true` 运行构建产物，避免首次编译占用 Optics 的 300 秒会话创建请求。`isHeadless: true` 与 `simctl boot` 的无窗口模式一致，避免 Appium 为显示 Simulator 窗口再次重启模拟器。WDA 启动只尝试一次、最多等待 120 秒，避免默认的多次等待超过客户端时限。配置依据 [XCUITest 7.35 预构建 WDA 文档](https://appium.github.io/appium-xcuitest-driver/7.35/guides/run-prebuilt-wda/) 和 [capabilities 文档](https://appium.github.io/appium-xcuitest-driver/7.35/reference/capabilities/)。

归档包含 CI 套件、JUnit、日志和截图，移动端还包含 `appium.log`。Android 在模拟器关闭前额外保存最近 2000 条 logcat 和 Activity 状态。截图名称可能含冒号，因此按照官方建议先压缩再上传。没有启用 `continue-on-error`。

iOS 归档额外包含 `wda-build.log` 和 Xcode 生成的 `wda-build.xcresult`（若已生成）。启用 `showXcodeLog` 后，WDA 运行阶段的 Xcode 输出会写入 `appium.log`；移动测试失败时也会在 Actions 控制台打印 Appium 日志末尾。如果创建会话超时并伴随 `127.0.0.1:8100` 连接拒绝，应先检查 WDA 构建和启动日志；后续 `NoneType.find_elements` 是会话创建失败后的连带错误。

首次登录控件超时时，先检查归档中的关闭应用前截图、页面树和 `logcat.txt`，判断是启动较慢、系统弹窗还是应用崩溃；仅凭 Activity 已启动不能证明登录界面已就绪。延长等待用于容纳云端冷启动，不能修复应用崩溃或被弹窗遮挡。Optics 的默认最终采集可能发生在应用关闭后，因此这里显式在移动端 teardown 中采集。

CI 在临时套件目录内执行 `optics execute . --no-use-printer`，不会调用桌面窗口适配器。项目固定使用 Optics 1.11.0，其 Playwright 驱动支持 `headless: true`；官方文档中针对 1.10.5 的 `xvfb-run` 兼容方案在这里不需要。本地 `./run-tests web` 仍保持最大化、有界面和减速行为。

## 固定版本与移动应用

- Python：3.12；Optics：1.11.0，分别在 `requirements-web.txt` / `requirements-mobile.txt` 中指定引擎。
- Node.js：22；Appium：2.11.3；UiAutomator2：2.45.1；XCUITest：7.35.0。
- Swag Labs：官方 [2.7.1 release](https://github.com/saucelabs/sample-app-mobile/releases/tag/2.7.1)，工作流固定下载 URL 和 SHA-256。

Android 下载 APK，安装到 `emulator-5554`。iOS 下载 **Simulator `.zip`**，解压后安装 `.app`；不能将真机 `.ipa` 用于模拟器。已核对下载包的 `com.saucelabs.SwagLabsMobileApp` Bundle ID 和 x86_64 架构，因此使用 Intel runner。模拟器不需要 Apple Developer 签名证书或真机 provisioning profile。

iOS 每次创建专属模拟器，运行结束后关闭并删除。CI 的设备 UDID 由 `simctl create` 生成，不使用本机 UDID。Web/Android/iOS 位于不同 runner，所以移动端 CI 均可使用 Appium `4723`；本地两服务的 `4723` / `4725` 配置不变。

Xcode 和 iOS runtime 使用明确版本；当 GitHub 更新或移除镜像中的工具时，需要一起调整 Xcode、runtime、设备类型及适配的 XCUITest 版本。参考 [GitHub macOS 镜像清单](https://github.com/actions/runner-images/blob/main/images/macos/macos-15-Readme.md) 和 [XCUITest 系统要求](https://appium.github.io/appium-xcuitest-driver/latest/getting-started/system-requirements/)。

## 本地检查

使用已安装 optics-framework 的 Python 环境：

```bash
python -m unittest discover -s ci -p 'test_*.py'
actionlint .github/workflows/optics-web.yml .github/workflows/optics-android.yml .github/workflows/optics-ios.yml
bash -n ci/run_mobile.sh
bash -n ci/build_wda.sh
```

`actionlint` 是工作流语法检查工具，需单独安装。完整的 GitHub runner 环境只能在仓库 Actions 中验证；本地静态检查或本地浏览器通过，不代表云端三端已经执行通过。
