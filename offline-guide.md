docker load -i .\vendor\images\node.tar
docker load -i .\vendor\images\python.tar
python .\update-brand-build.py --offline --image-tag open-webui:branded-offline