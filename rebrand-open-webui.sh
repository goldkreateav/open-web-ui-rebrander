git clone https://github.com/open-webui/open-webui.git 
python ./branding-tools/branding/apply_branding.py \
    --config ./branding-tools/branding/branding.config.json \
    --target-dir ./open-webui
cd ./open-webui
docker build -t open-webui:branded-fixed . 
read