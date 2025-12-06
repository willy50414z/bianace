from enum import Enum


class ApiUser(Enum):
    def __init__(self, value, acct_name):
        # 注意：Enum 成員的 value 必須作為第一個參數傳入
        self._value_ = value
        # 儲存額外的屬性
        self.acct_name = acct_name

    HEDGE_BUY = (1, "hedgebuy")
    WILLY_MOCK = (2, "willy50414z_mock")
