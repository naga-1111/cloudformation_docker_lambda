import asyncio
import aiohttp
import datetime
import itertools
import requests
import time
import sys
import pandas as pd
import time
import boto3


class TestError(Exception):
  pass


class bybit_data_manage:
  def __init__(self):
    """
    S3限定アクセス権限
    """
    self.client = boto3.client(
            's3',
            aws_access_key_id="",
            aws_secret_access_key="",
            region_name='ap-northeast-1')
    self.bucket_name = ""
    self.s3_path = ""
    return


  async def __fetch(self, session, url, coro):
      """HTTPリソースからデータを取得しコルーチンを呼び出す
      :param session: aiohttp.ClientSessionインスタンス
      :param url: アクセス先のURL
      :param coro: urlとaiohttp.ClientResponseを引数に取るコルーチン
      :return: coroの戻り値
      https://gist.github.com/rhoboro/86629f831934827d832841709abfe715
      """
      retry = 1
      while retry<=5:
        try:
            response = await session.get(url)
            return await coro(url, response)
        except Exception as e:
          print("retry in 60 sec")
          time.sleep(60)
          response = None
          retry+=1
      print("cannot solve error")
      sys.exit()


  async def __bound_fetch(self, semaphore, url, session, coro):
      """並列処理数を制限しながらHTTPリソースを取得するコルーチン
      :param semaphore: 並列数を制御するためのSemaphore
      :param session: aiohttp.ClientSessionインスタンス
      :param url: アクセス先のURL
      :param coro: urlとaiohttp.ClientResponseを引数に取るコルーチン
      :return: coroの戻り値
      """
      async with semaphore:
        await asyncio.sleep(1)
        return await self.__fetch(session, url, coro)


  async def __run(self, urls, coro, limit=1):
      """並列処理数を制限しながらHTTPリソースを取得するコルーチン
      :param urls: URLの一覧
      :param coro: urlとaiohttp.ClientResponseを引数に取るコルーチン
      :param limit: 並列実行の最大数
      :return: coroの戻り値のリスト。urlsと同順で返す
      """
      tasks = []
      semaphore = asyncio.Semaphore(limit)
      # [SSL: CERTIFICATE_VERIFY_FAILED]エラーを回避する
      async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
          for url in urls:
              task = asyncio.ensure_future(self.__bound_fetch(semaphore, url, session, coro))
              tasks.append(task)
          responses = await asyncio.gather(*tasks)
          return responses


  async def __coroutine(self, url, response):
    """url, responseを受け取る任意のコルーチン
    """
    #return url, response.status, await response.json()
    return await response.json()


  def __make_event_loop(self, urls, coro, limit=3):
    """並列処理数を制限しながらHTTPリソースを取得し、任意の処理を行う
    :param urls: URLの一覧
    :param coro: urlとaiohttp.ClientResponseを引数に取る任意のコルーチン
    :param limit: 並列実行の最大数
    :return: coroの戻り値のリスト。urlsと同順。
    """
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(self.__run(urls, coro, limit))
    return results


  def __async_main(self, urls):
    """
    """
    results = self.__make_event_loop(urls=urls, coro=self.__coroutine, limit=50)
    return results


  def __bybit_symbols(self):
      """
      全銘柄リスト作成
      """
      retryt = 10
      while (retryt <= 40):
          try:
              response = requests.get(f"https://api.bybit.com/derivatives/v3/public/tickers?category=linear")
              if response.status_code != 200:
                  raise TestError
              response = response.json()
              symbols = [ i["symbol"] for i in response["result"]["list"] ]
              print(response)
              return symbols
          except TestError:
              time.sleep(retryt)
              retryt *= 2


  def __make_url_list(self):
    """future,indexのohlcv取得用urlリスト作成
    """
    now_t = datetime.datetime.now()                             # 現在時刻
    now_t = int(now_t.timestamp())                              # unit : s

    #どこまで遡りたいかを決める
    int_max = now_t - int( ( pd.to_datetime("2021-01-01") ).timestamp() )     #unit : s
    int_max = int(int_max/60/5/200) + 1                                       #unit : -
    #startt = [ (now_t - 60*5*200*i)*1000 for i in range(1, int_max) ]         #unit : ms
    startt = [ (now_t - 60*5*200*i)*1000 for i in range(1, 3) ]               #テスト用

    def __url_str_list(symbol, starti):
      future = f"https://api.bybit.com/derivatives/v3/public/kline?category=linear&symbol={symbol}&interval=5&start={starti}&end={starti + 60*5*200*1000}&limit=200"
      index = f"https://api.bybit.com/derivatives/v3/public/index-price-kline?category=linear&symbol={symbol}&interval=5&start={starti}&end={starti + 60*5*200*1000}&limit=200"
      return [future, index]

    #urlリスト作成
    url_list = [__url_str_list(symbol, starti) for symbol in  self.__bybit_symbols() for starti in startt]     #テスト["BTCUSDT","ETHUSDT","BNBUSDT"] #self.__bybit_symbols()
    url_list = itertools.chain.from_iterable(url_list)                                                         # 3次元配列を平滑化
    url_list = list(url_list)
    print(f"symbol      : {len(self.__bybit_symbols())}")
    print(f"timestamp   : {len(startt)}")
    print(f'all tasks   : {len(list(url_list))}')
    return url_list


  def __json_to_dataframe(self,i):
    """jsonをDataFrame形式に変換
    """
    self.cols1 = ["timestamp","open","high","low","close","volume","turnover"]
    self.cols2 = ["timestamp","open_s","high_s","low_s","close_s"]
    try:
        if len(i["result"]["list"][0])==0:
            return
        elif len(i["result"]["list"][0])==7:
            df = pd.DataFrame(i["result"]["list"], columns=self.cols1)
        elif len(i["result"]["list"][0])==5:
            df = pd.DataFrame(i["result"]["list"], columns=self.cols2)
        else:
            df = pd.DataFrame(i["result"]["list"])
        df["symbol"] = i["result"]["symbol"]
        return df
    except TypeError:
        return pd.DataFrame(i["result"])    #lsだけv2でこっち


  def __arrange_df(self,df):
    """DataFrameを整理
    """
    self.cols1.append("symbol")
    self.cols2.append("symbol")

    df = pd.concat(df)                                                              #全部結合
    float_colmns = list( set(df.columns) -  set(["symbol"]))                        #floatにするべき列名リスト
    df[float_colmns] = df[float_colmns].astype(float)

    df_oi = df.dropna(subset=["openInterest"])                                      #oi列がNaNでない部分はoi用のdf
    df_oi = df_oi[["timestamp","symbol","openInterest"]].copy()

    df_future = df.dropna(subset=["close"])                                         #close列がNaNでない部分はfuture用のdf
    df_future = df_future[self.cols1].copy()

    df_index = df.dropna(subset=["close_s"])                                        #close_s列がNaNでない部分はindex用のdf
    df_index = df_index[self.cols2].copy()

    df_ls = df.dropna(subset=["buy_ratio"])                                         #buy_ratioがNaNでない部分はls用のdf
    df_ls = df_ls[["timestamp","symbol","buy_ratio","sell_ratio"]]
    df_ls["timestamp"] = df_ls["timestamp"].apply(lambda x: x*1000)                 #これだけv2でtimestampがms単位じゃなくてs単位

    df["timestamp"] = df["timestamp"].apply(lambda x: pd.to_datetime(x,unit="ms"))  #日付形式に変換
    df = pd.merge(df_future, df_index, on=["timestamp","symbol"])                   #再結合
    df = pd.merge(df, df_oi, on=["timestamp","symbol"])

    df = pd.merge(df, df_ls, on=["timestamp","symbol"])
    df.sort_values(by=["timestamp","symbol"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


  def __save_to_s3(self, df):
    """
    s3への保存
    """
    retryt = 10
    while retryt<=40:
        try:
            res = self.client.put_object(
                Body=df.to_csv(None,index=False),
                Bucket=self.bucket_name,
                Key=f'{self.s3_path}/{datetime.datetime.now().strftime("%Y-%m-%d_%H")}.csv',
            )
            res_status_code = res["ResponseMetadata"]["HTTPStatusCode"]
            if res_status_code != 200:
                raise TestError(f'response status is {res_status_code}')
            return
        except TestError:
            time.sleep(retryt)
            retryt*=2


  def main(self):
    url_list = self.__make_url_list()                         #urlリスト作成

    ###########################################
    print("\n===data get start===")
    print("api limit : 50it/s")

    results = self.__async_main(url_list)                     #全urlリストに対して非同期処理
    #with open("temp.json", "w") as f:                         #レスポンスの一時保存
      #json.dump(results, f)
    print("\n===data get end===")
    ###########################################

    df = [ self.__json_to_dataframe(i) for i in results ]     #全jsonをdf形式に変換
    del results

    df = self.__arrange_df(df)                                #dfを整理
    print(df)
    self.__save_to_s3(df)
    print("\n==end==")
    return

#if __name__ == "__main__":
def handler(event, context):
    bdm = bybit_data_manage()
    bdm.main()
