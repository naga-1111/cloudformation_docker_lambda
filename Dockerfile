FROM public.ecr.aws/lambda/python:3.9
COPY app.py ${LAMBDA_TASK_ROOT}

RUN pip3 install requests pandas boto3 asyncio aiohttp

CMD [ "app.handler" ]
