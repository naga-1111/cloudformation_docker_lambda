#cloudformationサンプル
##概要
DockerイメージをAmazon ECRにプッシュ、イメージからLambda関数作成して、5分おきに実行するイベントを作成するPowershellスクリプトとcloudformationテンプレートのサンプル
##環境の前提条件
* Docker for Windows
* AWS CLI https://docs.aws.amazon.com/ja_jp/cli/latest/userguide/getting-started-install.html
* `C:/Users/ユーザ名/.aws/`に、`credentialsサンプル`をコピーしてシークレット等記入して`credentials`という名前で保存
##使い方
* `app.py`を好きなように書き替える。
    * ただし、`def handler(event, context):` 内にメイン処理を書いてこの関数の名前は変えない、もしくは`template.yaml`内の該当箇所も修正する
* `template.yaml`を書き替える
    * 例えば`ScheduleExpression:`で好きな起動間隔に直す
* `deploy_tools.ps1`を書き替える
    * `$ProjectName`、`$Region_name`を好きに変える
    * `$AWSprofile`の値を、`crerdentials`の`[]`の値と同じにする
