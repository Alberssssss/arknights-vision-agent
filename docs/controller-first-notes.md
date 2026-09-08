# MAA／控制器优先：研究记录与下一步

更新：2026-09-08。用户要求把真实控制、自动战斗和完整肉鸽闭环提到视频
流水线之前。**已确认的是优先级，不是某个具体 SDK 设计或设备测试。**
本文件是方案比较与固定源码检查，不是已实现的控制器、完整规范或实施计划。

## 两条路线及建议顺序

| 路线 | 解决什么 | 仍然缺什么 |
| --- | --- | --- |
| A：接入现成 MAA／MaaCore 肉鸽自动化 | 在不训练本项目模型的前提下，建立指定环境上的自动化基线与结果记录 | 环境、主题/难度/队伍、受限测试、结果验收；不保证目标结局或稳定通关 |
| B：用 MaaFramework 执行自研策略 | 提供截图、点击和滑动等底层能力，供本项目未来策略调用 | 识图、状态跟踪、菜单/战斗策略、坐标校准、恢复和实测；SDK 本身不是肉鸽决策策略 |

建议先评审 A 的小范围接入，再逐步建设 B。A 的结果始终归因于 MAA 自带
策略，不能计成本项目模型的能力；如果用户要求从第一步就由自研策略决策，
需要单独确认该范围及感知/策略依赖。实际训练仍按用户要求留到后期。

游戏可能运行在另一台主机，不能从开发机是 Mac 推断目标平台。第一项待答
问题是 H04：游戏实际运行的平台、模拟器或设备。之后再固定 H01 的主题、
难度、结局和队伍，以及有限连接/截图/指定输入测试的范围。

## 本次核查到的 MAA 接口边界

本次检查固定于 MaaAssistantArknights 提交
`e523b2038c6790f5f45d95c2e1de84c3450cc357`，不是“最新版”承诺。
协调者直接读取了下面六个官方文件，核对返回内容的 Git blob 身份并检查
关键行；独立源码检查得到相同的主要结论。没有构建或加载 MaaCore，没有
连接设备，也没有改变现有配置报告的固定研究快照。

1. **语言绑定不等于完整 C API。** 所查 Python 包装提供同步 `connect`、
   `get_image`、`append_task`、`start`、`stop`、`running`；C API 另有
   `AsstAsyncConnect`、`AsstAsyncClick`、`AsstAsyncScreencap` 三个异步接口。
   不能编造现成的同名 Python 异步方法。Python `get_image(size)` 已调用
   `AsstGetImage`，但读取的是上次截图，不是发起新截图。Python `stop`
   停止并清空该实例任务，与现有“停止本项目代理”语义不同。
2. **肉鸽任务不等于通关模式。** `Roguelike` 的 `mode=0` 是刷分、尽量
   到达更高层，并非通关保证。模式 1 会在一层投资后退出；2 和 3 被拒绝。
   不能拿刷资源或主动退出的配置证明完整目标通关。
3. **次数和目标必须显式约束。** `starts_count` 默认是 2147483647；未来
   实验应明确有限次数及独立总时限。所请求难度未解锁时会改用最高已解锁
   难度，因此配置值不是“实际按该难度进行”的证明。
4. **队列结束不是通关证据。** `Assistant.cpp` 中，任务链错误之后仍可能
   因队列为空发出 `AllTasksCompleted`。任务链完成和队列完成必须分别记录，
   不能直接写成 `game_clear_verified=true`。
5. **结算信号有范围和缺失情况。** 所查插件用 `RoguelikeSettlement` 的
   `details.game_pass` 报告识别结果，只在 `Exp` 或 `BlackFlowBabyAnimal`
   模式启用。等待完整结算页失败时会直接返回、不发这个回调。缺失应记未知；
   已有信号仍需保留结算画面、身份及目标条件供验收。
6. **参数更新不等于实时策略注入。** 所查 `RoguelikeTask::set_params` 在
   任务运行时返回 false。不能假定通过通用参数更新接口就能随时接管整局。

固定官方来源：

- [集成与肉鸽任务参数](https://raw.githubusercontent.com/MaaAssistantArknights/MaaAssistantArknights/e523b2038c6790f5f45d95c2e1de84c3450cc357/docs/en-us/protocol/integration.md)：770–895 行。
- [C API 头文件](https://raw.githubusercontent.com/MaaAssistantArknights/MaaAssistantArknights/e523b2038c6790f5f45d95c2e1de84c3450cc357/include/AsstCaller.h)：60–135 行。
- [Python 包装](https://raw.githubusercontent.com/MaaAssistantArknights/MaaAssistantArknights/e523b2038c6790f5f45d95c2e1de84c3450cc357/src/Python/asst/asst.py)：130–230 行。
- [任务队列结束逻辑](https://raw.githubusercontent.com/MaaAssistantArknights/MaaAssistantArknights/e523b2038c6790f5f45d95c2e1de84c3450cc357/src/MaaCore/Assistant.cpp)：660–692 行。
- [肉鸽结算插件](https://raw.githubusercontent.com/MaaAssistantArknights/MaaAssistantArknights/e523b2038c6790f5f45d95c2e1de84c3450cc357/src/MaaCore/Task/Roguelike/RoguelikeSettlementTaskPlugin.cpp)：11–62 行。
- [运行中参数更新边界](https://raw.githubusercontent.com/MaaAssistantArknights/MaaAssistantArknights/e523b2038c6790f5f45d95c2e1de84c3450cc357/src/MaaCore/Task/Interface/RoguelikeTask.cpp)：209–220 行。

直接读取使用公开 GitHub contents API、有限超时和响应大小上限。第一次用
本机 Python HTTPS 客户端在证书校验阶段失败，随后用保留证书校验的系统
HTTPS 客户端成功读取；未修改网络、证书或全局配置。这是选定源码检查，
不是发行二进制、安装兼容性、全面源码审计或真实运行验证。

## MaaFramework 路线需保留的已有检查

既有 [MaaFramework 说明](maaframework-integration-notes.md) 固定于 `v5.12.3`，
它与上述 MaaCore 来源不是同一个项目。已有记录指出：异步作业返回不等于
成功，`wait()` 没有超时参数，截图 getter 读取最新缓存而不是某个作业的
不可变帧。因此未来适配器需要串行协调和自己的期限；期限到达不证明已经
提交的输入被取消。本次没有重新运行这些 SDK。

## 拟议验收顺序，尚未执行

1. **确定环境和设计。** 得到目标平台/设备信息后，评审最小接口规范、坐标
   空间、运行限制、失败状态、日志隐私和人工停止方式，再写文件级实施计划。
2. **离线适配器测试。** 用注入的替身测试连接失败、过期/错配截图、尺寸变化、
   超时、重复回调、迟到结果和异常清理。默认路径不导入 SDK、不发现设备、
   不执行动作；替身通过不等于真实兼容性。
3. **H04 的指定目标校准。** 先有界连接并读取截图，再执行用户确认的单次
   无购买/账户操作输入，读取新画面核验实际效果。不确定时停止后续派发，
   不通过盲目重试猜测输入是否已经发生。
4. **监督下的一场战斗。** 固定关卡和队伍，记录控制请求、任务状态、画面证据、
   超时/失败与人工介入，不能只检查返回值。
5. **H07 的有限整局实验。** 固定主题、难度、结局、总次数/时限及停止条件。
   每次尝试均计入，分别记录成功、失败、未知和人工介入，保留结果证据与
   策略来源。一次成功不等于可靠自动通关，MAA 基线也不等于模型进步。

这些是待评审的阶段目标，不是新接口已获批准的声明。H04/H07 不替代真实
录像 H02/H03 或训练启动的独立决定；H08 仍是更后的另一个视频设计事项。
