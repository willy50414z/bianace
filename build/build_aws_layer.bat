cd ..
mkdir target/python
robocopy com target/python /MIR
conda activate binance
pip freeze > target/python/requirements.txt
cd target/python
pip install --target . -r requirements.txt
cd ..
PowerShell -NoProfile -Command "Compress-Archive -Path '.\python' -DestinationPath 'python.zip'"
xcopy "libs\" "." /E /I /Y