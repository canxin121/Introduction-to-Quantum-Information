"""Superdense coding."""

# Imports
import qiskit

def bitstring(bits):
    return ''.join('1' if b else '0' for b in bits)


# Create two quantum and classical registers
qreg = qiskit.QuantumRegister(2)
creg = qiskit.ClassicalRegister(2)
circ = qiskit.QuantumCircuit(qreg, creg)

# Alice chooses a 2-bit message to send
message = "01"
print("Alice's sent message =", message)

# Alice and Bob share a Bell pair
circ.h(qreg[0])
circ.cx(qreg[0], qreg[1])

# Alice encodes her message on her qubit
if message[0] == "1":
    circ.z(qreg[0])
if message[1] == "1":
    circ.x(qreg[0])

# Bob decodes in the Bell basis
circ.cx(qreg[0], qreg[1])
circ.h(qreg[0])

# Add a Measure gate to obtain the message
circ.measure(qreg, creg)

# Print out the circuit
print("Circuit:")
print(circ.draw())

# Run the quantum circuit on a simulator backend
from qiskit.primitives import StatevectorSampler
sampler = StatevectorSampler()
job = sampler.run([circ], shots=1024)
res = job.result()
counts = res[0].data.c0.get_counts()
print("Measurement results:", counts)

# Qiskit returns classical bits as c[1]c[0], reverse for q0q1 order
most_likely = max(counts, key=counts.get)
received = most_likely[::-1]
print("Bob's received message =", received)
