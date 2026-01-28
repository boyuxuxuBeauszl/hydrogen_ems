# Hydrogen Hybrid Energy Management System (Hydrogen EMS)

This repository contains a modular energy management system for a hydrogen-based hybrid powertrain, designed for real-time supervisory control using a Raspberry Pi and an STM32-based low-level controller.

The system integrates:
- Classical control (e.g. rule-based or MPC)
- Reinforcement learning (DQN) as a supervisory decision layer
- Real-time communication with embedded hardware

This project is intended for research, prototyping, and experimental validation.

---

## System Architecture

High-level control and supervision are deployed on a Raspberry Pi, while low-level motor control is handled by an STM32 microcontroller.

[ Sensors / Vehicle State ]
↓
STM32 (Low-level control)
↓
Raspberry Pi (Supervisory Layer)
- State management
- DQN-based decision making
- Health monitoring
- Data logging
↓
Control adjustment / command


---

## Project Structure

hydrogen_ems/
├── config/ # Configuration files
│ └── config.yaml
├── core/ # Learning-based decision modules
│ └── dqn_agent.py
├── communication/ # Communication with STM32 / simulator
│ ├── protocol.py
│ ├── serial_comm.py
│ ├── udp_comm.py
│ └── mock_comm.py
├── modules/ # System-level functional modules
│ ├── supervisor.py
│ ├── health_monitor.py
│ ├── data_recorder.py
│ └── state_manager.py
├── utils/ # Utilities
│ ├── logger.py
│ └── config_loader.py
├── tests/ # Unit tests
├── logs/ # Runtime logs (ignored by git)
├── data/ # Recorded trajectory data (ignored by git)
├── main.py # Program entry point
└── requirements.txt


---

## Control Logic Overview

- STM32 executes low-level control of actuators (e.g. motor speed control)
- Raspberry Pi operates as a **supervisory controller**
- The DQN agent does not directly control actuators
- Instead, it provides **adjustments or corrections** to a baseline strategy (e.g. MPC or rule-based control)

This structure improves:
- Safety
- Interpretability
- Deployability on real hardware

---

## Data Recording

The system supports structured data logging for:
- State trajectories
- Control actions
- Health and diagnostic signals

Recorded data can be used for:
- Offline analysis
- Training reinforcement learning models
- Debugging and performance evaluation

---

## Running the System

1. Install dependencies:
```bash
pip install -r requirements.txt
Configure system parameters:

config/config.yaml
Run the main program:

python main.py
Intended Hardware
Raspberry Pi (supervisory controller)

STM32 microcontroller (low-level control)

Motor driver and sensors

Remote controller (manual override / testing)

Notes
The system is designed to be modular and extensible

Communication modules can be replaced or mocked for testing

Data and logs are excluded from version control by design

License
This project is currently intended for research and educational use.

