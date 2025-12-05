pip freeze > requirements.txt
cd ..
RD /S /Q "target"
robocopy com target/com /MIR

xcopy "build\requirements.txt" "target" /E /I /Y
xcopy "build\Dockerfile" "target" /E /I /Y

cd target
docker build -t ma_7_25_break .
docker container rm -f ma_7_25_break
docker run --name ma_7_25_break -p 9000:8080 -d ma_7_25_break

cd ..
RD /S /Q "target"

docker tag ma_7_25_break 449068335280.dkr.ecr.us-east-1.amazonaws.com/binance_trade_bot/ma_7_25_break:latest
docker push 449068335280.dkr.ecr.us-east-1.amazonaws.com/binance_trade_bot/ma_7_25_break:latest
