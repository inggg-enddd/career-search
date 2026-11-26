# GMP 验证 Demo

三个能跑出结论的小实验，用来把「听说过的调度器行为」变成「亲眼见过的行为」。

```bash
cd demos/gmp
./run.sh            # 依次跑三个
```

或单独跑：

```bash
go run ./01-runnext
go run ./02-gosched
cd 03-preempt && go build -o preempt_demo . && ./preempt_demo
```

---

## Demo 1 · runnext：新 G 会插队

**问题**：`go f()` 创建的 G 是进入「本地队列」还是别的地方？

**实测输出**（Go 1.27.1 / darwin-arm64，`GOMAXPROCS=1`）：

```
GOMAXPROCS=1

3 个 goroutine                创建顺序 0..2  →  执行顺序 [2 0 1]
5 个 goroutine                创建顺序 0..4  →  执行顺序 [4 0 1 2 3]
8 个 goroutine                创建顺序 0..7  →  执行顺序 [7 0 1 2 3 4 5 6]
```

**结论**：最后一个创建的先跑，其余从 0 开始 FIFO。

这正是 `runtime.runqput(pp, gp, next=true)` 的行为：新 G 写入 `p.runnext`（覆盖式，只存一个），被顶掉的那个才进本地 `runq` 尾部。

> 注意：所以「Go 的调度是后进先出」这句话是**错的**。只有 `runnext` 一个位置是插队，其余仍是 FIFO。这个细节在面试里能直接区分「读过源码」和「看过二手文章」。

---

## Demo 2 · Gosched：主动让出的代价

**问题**：`runtime.Gosched()` 说「让出 CPU」，让出的 G 去哪了？

**实测输出**：

```
== 场景一：Gosched 会改变执行顺序 ==
执行日志：[C A-start B A-resume]

== 场景二：Gosched 的代价 ==
不让出       ：261.042µs   (checksum 134999550000)
每 1000 次让出：443.042µs   (checksum 134999550000)
倍率         ：约 2x
```

**结论一**：`Gosched` 不是把 G 放回本地 runq，而是塞进**全局队列** `sched.runq`。所以 A 让出后，本地队列的 B 先跑，A 要等全局队列被取才回来。

**结论二**：全局队列要抢 `sched.lock`，所以主动让出比不让出慢。这也是为什么生产代码里几乎不该出现 `Gosched`——它是调试/教学工具，不是性能优化手段。

> 顺带理解那条「每 61 次调度才取全局队列」：既然取全局要加锁，就不能每次调度都抢，否则本地队列的收益全被锁吃掉。61 是个经验质数，避免与 P 数量共振。

---

## Demo 3 · 异步抢占：死循环能不能被叫停

**问题**：Go 1.14 引入异步抢占，到底解决了什么？

**场景**：`GOMAXPROCS=1`，一个 `for {}`（内部**没有任何函数调用**，因此没有协作式抢占点）霸占 P，另一个 goroutine 每 100ms 打印。

**默认行为**：

```
GOMAXPROCS=1，启动一个空转 goroutine（for {}，无函数调用）
  tick 1  经过 112ms
  tick 2  经过 236ms
  tick 3  经过 357ms
  tick 4  经过 479ms
  tick 5  经过 602ms

结论：空转的 G 被异步抢占，其他 goroutine 仍能推进。
```

**关闭异步抢占**（`GODEBUG=asyncpreemptoff=1`）：

```
GOMAXPROCS=1，启动一个空转 goroutine（for {}，无函数调用）
（然后进程卡死，被外部 alarm 杀掉）
```

**结论**：

1. 默认情况下，sysmon 发现 P 被占用超过 10ms，会向该 M 发 `SIGURG`；信号处理器打上抢占标记，G 走到安全点后让出。
2. 关掉之后，空转 G 永远不会让出——**连 demo 自己的 3 秒超时都无法触发**，因为定时器也需要 P 才能运行。这是「一个 goroutine 能让整个程序失去响应」的最直观演示。
3. 所以 1.14 之前，「写了个带死循环的 goroutine 导致服务卡死」是真实会发生的生产事故。

---

## 三个 demo 的共同前提

都用 `runtime.GOMAXPROCS(1)`。单核能把「并行」排除掉，让「调度顺序」变得可观测——多核下 G 可能真的同时在跑，顺序就不可复现了。

这也是排查调度问题时的一个实用技巧：**先把 GOMAXPROCS 压到 1，让问题复现，再放大。**
