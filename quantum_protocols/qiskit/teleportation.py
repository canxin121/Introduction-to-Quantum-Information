"""Quantum teleportation in Qiskit."""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import  IGate, XGate, ZGate
import numpy as np

# Create quantum and classical registers
q = QuantumRegister(3, 'q')
c0 = ClassicalRegister(2, 'creg_alice')
c1 = ClassicalRegister(1, 'creg_bob')
qc = QuantumCircuit(q, c0, c1)

# Prepare the message qubit (qubit 0) in a specific state
# For example: |ψ⟩ = α|0⟩ + β|1⟩
qc.h(q[0])
qc.t(q[0])

# Create entangled Bell pair between Alice (qubit 1) and Bob (qubit 2)
qc.h(q[1])
qc.cx(q[1], q[2])

qc.barrier(q)

# Bell measurement: Alice performs CNOT and H on her qubits
qc.cx(q[0], q[1])
qc.h(q[0])

# Measure Alice's qubits
qc.measure([q[0], q[1]], c0)

qc.barrier(q)

# Bob applies corrections based on Alice's measurements
# Using c_if for conditional operations
with qc.if_test((c0[1], 1)):  # If second classical bit is 1
    qc.x(q[2])

with qc.if_test((c0[0], 1)):  # If first classical bit is 1
    qc.z(q[2])

# Measure Bob's qubit to verify teleportation
qc.measure(q[2], c1)

print("Quantum Teleportation Circuit:")
print(qc.draw())
print("\nCircuit depth:", qc.depth())
print("Number of qubits:", qc.num_qubits)
print("\nQuantum teleportation protocol:")
print("1. Alice prepares a message qubit |ψ⟩")
print("2. Alice and Bob share an entangled Bell pair")
print("3. Alice performs Bell measurement on message qubit and her half of the Bell pair")
print("4. Alice sends 2 classical bits to Bob")
print("5. Bob applies corrections based on Alice's measurement results")
print("6. Bob's qubit is now in the state |ψ⟩")