#!/bin/bash
cd /home/bvb/bvb-data-worker
set -a; source .env; set +a
.venv/bin/python3 src/iris_sync.py "SNP,EL,TLV,AQU,BAY,BRD,DIGI,FP,H2O,HANL,M,MEDIAT,SFG,SNN,TGN,TLV,TRP" >> logs/iris_sync.log 2>&1
