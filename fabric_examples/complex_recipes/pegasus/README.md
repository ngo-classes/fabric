# Pegasus-FABRIC: Distributed Workflow Infrastructure on FABRIC Testbed

Deploy and manage Pegasus WMS and HTCondor clusters on the FABRIC testbed for distributed scientific workflow execution.

## Overview

This repository provides Jupyter notebooks and provisioning scripts to create distributed Pegasus/HTCondor infrastructure on FABRIC. The setup includes:

- **Submit Node**: Central HTCondor manager with Pegasus WMS for workflow submission
- **Worker Nodes**: HTCondor execute nodes distributed across FABRIC sites
- **Edge Workers** (Optional): DPU-enabled nodes for edge-to-cloud workflows

### Architecture

```
                    ┌─────────────────────┐
                    │    Submit Node      │
                    │  (Central Manager)  │
                    │  - HTCondor CM      │
                    │  - Pegasus WMS      │
                    │  - Singularity      │
                    └──────────┬──────────┘
                               │ FABNet IPv4
        ┌──────────────────────-──────────────────────┐
        │                                             │
        ▼                                             ▼
┌───────────────┐                              ┌───────────────┐
│ Worker Node 1 │                              │ Worker Node 2 │
│   (UCSD)      │                              │   (FIU)       │
│ - HTCondor    │                              │ - HTCondor    │
│ - Singularity │                              │ - Singularity │
└───────────────┘                              └───────────────┘
```

## Prerequisites

### FABRIC Requirements

- FABRIC account with valid credentials
- Project membership with sufficient resource allocation
- FABlib installed and configured
- SSH keys configured for FABRIC bastion access

### Software Requirements

- Python 3.9+
- Jupyter Notebook/Lab
- FABlib (`pip install fabrictestbed-extensions`)

## Directory Structure

```
pegasus-fabric/
├── pegasus-fabric.ipynb       # Main deployment notebook
├── node_tools/                # Provisioning scripts
│   ├── htcondor.sh           # HTCondor installation
│   ├── pegasus.sh            # Pegasus WMS installation
│   ├── fabric-submit.sh      # Submit node configuration
│   ├── fabric-worker.sh      # Standard worker configuration
└── README.md
```

## Quick Start

### 1. Configure FABRIC Environment

Ensure your FABRIC credentials are configured:

```bash
# Set environment variables or configure fabric_rc file
export FABRIC_CREDMGR_HOST=cm.fabric-testbed.net
export FABRIC_ORCHESTRATOR_HOST=orchestrator.fabric-testbed.net
export FABRIC_TOKEN_LOCATION=/path/to/tokens.json
export FABRIC_BASTION_USERNAME=your-username
export FABRIC_BASTION_KEY_LOCATION=/path/to/bastion_key
export FABRIC_SLICE_PRIVATE_KEY_FILE=/path/to/slice_key
export FABRIC_SLICE_PUBLIC_KEY_FILE=/path/to/slice_key.pub
```
Alternatively, you can run this [notebook](https://github.com/fabric-testbed/jupyter-examples/blob/main/configure_and_validate/configure_and_validate.ipynb) to configure your FABRIC environment.

### 2. Launch Jupyter and Open Notebook

```bash
jupyter notebook pegasus-fabric.ipynb or upload it to FABRIC Jupyter Lab and run the notebook. 
```

### 3. Configure Deployment

Edit the configuration section in the notebook:

```python
# Sites for worker nodes
site_names = ['UCSD', 'CLEM', 'TACC', 'MICH']

# Submit node configuration
fabric_submit_site = 'LOSA'
fabric_submit_cores = 16
fabric_submit_ram = 32
fabric_submit_disk = 500

# Worker node configuration (per site)
worker_cores = 24
worker_ram = 48
worker_disk = 500
```

### 4. Run Notebook Cells

Execute cells sequentially to:
1. Create FABRIC slice with submit and worker nodes
2. Configure FABNet IPv4 networking
3. Install HTCondor and Pegasus on all nodes
4. Set up SSH key exchange between nodes
5. Configure /etc/hosts for hostname resolution
6. Start HTCondor daemons

### 5. Verify Deployment

SSH to the submit node and verify:

```bash
# Check HTCondor status
condor_status

# Check Pegasus
pegasus-version

# View worker nodes
condor_status -schedd
```

## Provisioning Scripts

### htcondor.sh

Installs HTCondor using the official quick install method:

```bash
./htcondor.sh --no-dry-run
```

### pegasus.sh

Installs Pegasus WMS from the official repository:

```bash
./pegasus.sh --no-dry-run
```

### fabric-submit.sh

Configures the submit node as HTCondor Central Manager:

```bash
./fabric-submit.sh <interface> <submit_ip> <submit_hostname>
```

Features:
- HTCondor Central Manager configuration
- Singularity and Docker installation
- AWS CLI for S3 access
- Pegasus credentials setup

### fabric-worker.sh

Configures standard cloud worker nodes:

```bash
./fabric-worker.sh <interface> <submit_ip> <submit_hostname>
```

Features:
- HTCondor execute node configuration
- Singularity runtime
- Connection to Central Manager

## Workflow Examples

The following workflow repositories are designed to run on this infrastructure:

- [orcasound-workflow](https://github.com/pegasus-isi/orcasound-workflow): Hydrophone audio processing for Orca detection
- [earthquake-workflow](https://github.com/pegasus-isi/earthquake-workflow): Seismic data analysis and prediction
- [soilmoisture-workflow](https://github.com/pegasus-isi/soilmoisture-workflow): Agricultural soil moisture analysis
- [crophealth-workflow](https://github.com/pegasus-isi/crophealth-workflow): Crop disease detection from images
- [airquality-workflow](https://github.com/pegasus-isi/airquality-workflow): Air Quality forecasting

### Running a Workflow

```bash
# SSH to submit node
ssh ubuntu@<submit_node_ip>

# Clone workflow repository
git clone https://github.com/pegasus-isi/earthquake-workflow
cd earthquake-workflow

# Generate workflow
./workflow_generator.py --regions california --output workflow.yml

# Plan and submit
pegasus-plan --submit -s condorpool -o local workflow.yml

# Monitor
pegasus-status <run_directory>
```

## Slice Management

### Extend Slice Lease

```python
from datetime import datetime, timedelta
from dateutil import tz

end_date = (datetime.now(tz=tz.tzutc()) + timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S %z")
slice = fablib.get_slice(name=fabric_slice_name)
slice.renew(end_date)
```

### Delete Slice

```python
slice = fablib.get_slice(fabric_slice_name)
slice.delete()
```

## Troubleshooting

### HTCondor Issues

```bash
# Check condor logs
sudo tail -f /var/log/condor/MasterLog
sudo tail -f /var/log/condor/SchedLog
sudo tail -f /var/log/condor/StartLog

# Restart condor
sudo systemctl restart condor

# Check configuration
condor_config_val -dump | grep -i central
```

### Network Issues

```bash
# Verify FABNet connectivity
ping <other_node_hostname>

# Check /etc/hosts
cat /etc/hosts

# Verify interface configuration
ip addr show
```

### Pegasus Issues

```bash
# Check Pegasus logs
pegasus-analyzer <run_directory>

# View job logs
cat <run_directory>/work/<job>/*.err
cat <run_directory>/work/<job>/*.out
```

## Resource Recommendations

| Node Type | Cores | RAM (GB) | Disk (GB) | Use Case |
|-----------|-------|----------|-----------|----------|
| Submit | 16 | 32 | 500 | Central Manager + Planning |
| Standard Worker | 24 | 48 | 500 | General compute |
| ML Worker | 32+ | 64+ | 500 | ML training/inference |

## Related Resources

- [FABRIC Testbed](https://portal.fabric-testbed.net/)
- [FABlib Documentation](https://fabric-fablib.readthedocs.io/)
- [Pegasus WMS Documentation](https://pegasus.isi.edu/documentation/)
- [HTCondor Manual](https://htcondor.readthedocs.io/)

## License

This project is released under the same license as the parent repository.

## Authors

Komal Thareja (kthare10@renci.org)

Built with the assistance of Claude.
