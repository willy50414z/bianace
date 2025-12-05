cd ..
RD /S /Q "target"
robocopy com target/python /MIR

xcopy "build\requirements.txt" "target\python" /E /I /Y
xcopy "build\Dockerfile" "target" /E /I /Y

cd target
docker build -t lambdas_build .
docker container rm -f lambdas_build
docker run --name lambdas_build -d lambdas_build
docker exec -it lambdas_build pip install --target . -r requirements.txt
docker exec -it lambdas_build dnf update -y
docker exec -it lambdas_build dnf install zip -y
docker exec -it lambdas_build zip -r /var/task/python.zip .
docker cp lambdas_build:/var/task/python.zip ./
@REM pip install --target . -r requirements.txt
@REM dnf update -y
@REM dnf install zip -y
@REM zip -r /var/task/python.zip .
@REM docker cp lambdas_build:/var/task/python.zip ./