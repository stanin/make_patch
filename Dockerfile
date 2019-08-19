FROM centos

EXPOSE 80

RUN mkdir -p /root/test_dir && cd /root/test_dir
WORKDIR /root/test_dir
ADD ./test.sh .

CMD ./test.sh
