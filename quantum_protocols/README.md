# 量子协议实现：量子超密编码与量子隐形传态

## 快速开始

1. 创建虚拟环境并安装依赖（使用 uv）

```bash
uv venv .venv
uv pip install -e . --python .venv/bin/python
```

2. 运行各个代码

如果你使用bash终端，可以运行以下命令：

```bash
source .venv/bin/activate
mkdir -p output
python cirq/superdense-coding-cirq.py > output/superdense-coding-cirq.txt
python cirq/teleportation-cirq.py > output/teleportation-cirq.txt
python cirq/bell-inequality-test.py > output/bell-inequality-test.txt
python qiskit/superdense-coding.py > output/superdense-coding.txt
python qiskit/teleportation.py > output/teleportation.txt
```

如果你使用fish终端，可以运行以下命令：

```bash
source .venv/bin/activate.fish
mkdir -p output
python cirq/superdense-coding-cirq.py > output/superdense-coding-cirq.txt
python cirq/teleportation-cirq.py > output/teleportation-cirq.txt
python cirq/bell-inequality-test.py > output/bell-inequality-test.txt
python qiskit/superdense-coding.py > output/superdense-coding.txt
python qiskit/teleportation.py > output/teleportation.txt
```

## 代码说明与实现要点

### `cirq/superdense-coding-cirq.py`

**做什么**：用 Cirq 演示量子超密编码（1 个量子比特携带 2 个经典比特信息）。

**怎么实现**：
- 创建两比特电路，先用 `H` + `CNOT` 生成 Bell 纠缠态。
- Alice 固定发送消息 `m="01"`，根据字典映射对她的量子比特施加 `X` 或 `Z`。
- Bob 用 `CNOT` + `H` 做 Bell 基测量前的解码，再测量两比特。
- 使用 `cirq.Simulator` 运行 1 次并打印电路与接收结果。

---

### `cirq/teleportation-cirq.py`

**做什么**：用 Cirq 演示量子隐形传态，并用布洛赫球坐标验证传态前后量子态一致。

**怎么实现**：
- 三个量子比特：`msg`（待传态）、`alice`、`bob`。
- 先用 `H` + `CNOT` 在 `alice` 和 `bob` 上制备 Bell 纠缠。
- 用 `X**ranX`、`Y**ranY` 在 `msg` 上准备一个随机量子态。
- 对 `msg` + `alice` 做 Bell 测量（`CNOT` + `H` + 测量）。
- 用测量得到的经典信息在 `bob` 上做修正（`CNOT` 与 `CZ`）。
- 分别计算传态前后的 Bloch 向量并打印对比。

---

### `cirq/bell-inequality-test.py`

**做什么**：构造一个等价于 Bell 不等式（CHSH）测试的量子线路，统计赢率。

**怎么实现**：
- 四个量子比特：Alice、Bob、以及两个“裁判”比特。
- Alice/Bob 共享纠缠态（`H` + `CNOT` + `X**-0.25`）。
- 两个裁判通过 `H` 生成随机输入 `x,y`。
- Alice/Bob 根据裁判输入执行受控的 `sqrt(X)` 旋转。
- 测量得到 `a,b,x,y`，检验条件 `(a XOR b) == (x AND y)` 并统计赢率。

---

### `qiskit/superdense-coding.py`

**做什么**：用 Qiskit 演示量子超密编码，固定发送一个 2 比特消息并解码验证。

**怎么实现**：
- 构建 2 量子比特 + 2 经典比特电路。
- Alice/Bob 先制备 Bell 纠缠（`H` + `CX`）。
- Alice 固定发送 `message="01"`，对自己的比特施加 `Z`/`X` 编码。
- Bob 通过 `CX` + `H` 做 Bell 基解码并测量。
- 使用 `StatevectorSampler` 进行 1024 次采样，输出计数分布与解码结果。

---

### `qiskit/teleportation.py`

**做什么**：用 Qiskit 构建量子隐形传态线路并打印线路结构与步骤说明。

**怎么实现**：
- 三个量子比特：`q0` 作为消息比特，`q1/q2` 为纠缠对。
- 用 `H` 和 `T` 在 `q0` 上准备具体量子态。
- 在 `q1/q2` 上制备 Bell 纠缠（`H` + `CX`）。
- 对 `q0/q1` 做 Bell 测量，并将结果写入经典寄存器。
- 使用 `if_test` 根据经典比特对 `q2` 施加条件修正（`X`/`Z`）。
- 打印线路、深度、量子比特数和协议步骤说明。
