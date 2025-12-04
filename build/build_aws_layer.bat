cd ..
RD /S /Q "target"
robocopy com target/python /MIR

xcopy "build\requirements.txt" "target\python" /E /I /Y
cd target/python
pip install --target . -r requirements.txt
cd ..

pip install --target . -r requirements.txt

dnf update -y
dnf install zip -y

cd ..
zip -r /var/task/python.zip .

docker cp naughty_nightingale:/var/task/python.zip ./