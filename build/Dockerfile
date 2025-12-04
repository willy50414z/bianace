# 使用 AWS Lambda 官方 Python 基礎映像
# 建議使用最新的穩定版本，例如 Python 3.12
FROM public.ecr.aws/lambda/python:3.14

# 設定容器內的工作目錄
WORKDIR /var/task



# 複製您的整個 python 資料夾到容器的 /var/task
# /var/task 是 Lambda 執行時存儲程式碼的標準路徑
# 您的程式碼和 requirements.txt 現在位於 /var/task/python/
COPY python /var/task/python

# 為了方便手動進入容器後操作，將工作目錄切換到 python 資料夾
# 這樣您進入容器後就可以直接看到 requirements.txt
WORKDIR /var/task/python

# 為了讓容器啟動後能持續運行，將 ENTRYPOINT 設置為無限循環
# 這很重要，否則容器執行完預設 ENTRYPOINT 後會立即退出
ENTRYPOINT ["/bin/bash"]
CMD ["-c", "tail -f /dev/null"]