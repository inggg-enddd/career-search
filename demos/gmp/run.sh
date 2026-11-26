#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "########## Demo 1 · runnext ##########"
(cd 01-runnext && go run main.go)
echo
echo "########## Demo 2 · Gosched ##########"
(cd 02-gosched && go run main.go)
echo
echo "########## Demo 3 · 异步抢占 ##########"
cd 03-preempt
go build -o preempt_demo .
perl -e 'alarm 6; exec @ARGV' ./preempt_demo || true
echo
echo "提示：想看「没有异步抢占」的对照，跑："
echo "  GODEBUG=asyncpreemptoff=1 ./03-preempt/preempt_demo"
echo "（会卡死，用 Ctrl-C 或外部 timeout 结束——这本身就是结论）"
