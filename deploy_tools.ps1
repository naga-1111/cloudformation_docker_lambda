$ProjectName = "bybit5min"

$DockerTag = "$ProjectName" + ":latest"
$Region_name = "ap-northeast-1"
$AWSprofile = "deve1"

#接続通信テスト
#aws s3 ls --profile $AWSprofile
#exit

##Dockerイメージビルド
docker build -t "$DockerTag" .


#イメージを保存するAWSのECRを作成
$ECR_repo_id = aws ecr create-repository `
--repository-name $ProjectName `
--query 'repository.registryId' `
--profile $AWSprofile

$ECR_repo_id


#既に同じ名前で作成されてたら、そのECRのid取得
if ($lastexitcode -ne 0){
  $ECR_repo_id = aws ecr describe-repositories `
                --repository-name $ProjectName `
                --query "repositories[0].registryId" `
                --profile $AWSprofile
  $ECR_repo_id
}


#ECRにログイン
aws ecr get-login-password --profile $AWSprofile | `
docker login --username AWS `
--password-stdin "$ECR_repo_id.dkr.ecr.$Region_name.amazonaws.com"


#イメージをプッシュ
docker tag $DockerTag "$ECR_repo_id.dkr.ecr.$Region_name.amazonaws.com/$DockerTag"
docker push "$ECR_repo_id.dkr.ecr.$Region_name.amazonaws.com/$DockerTag"


#テンプレートからデプロイ
aws cloudformation deploy `
--stack-name $ProjectName `
--template-file ./template.yaml `
--parameter-overrides EcrImageUri="$ECR_repo_id.dkr.ecr.$Region_name.amazonaws.com/$DockerTag" `
--capabilities CAPABILITY_IAM `
--profile $AWSprofile
