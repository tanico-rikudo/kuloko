#!/bin/bash
#load common setting
eval 'source $BASE_DIR/geco_commons/shell/shell_config.conf'

function usage() {
  cat <<_EOT_
Usage:
  $0 [-a] [-b] [-f filename] arg1 ...

Description:
  hogehogehoge

Options:
  -r    Feed record
  -p    Feed fetch and provider
  -l    Feed hist data
  -k    Sender killer
  -g   general config mode
  -a   private api mode
  -s   symbol
_EOT_
  exit 1
}

if [ "$OPTIND" = 1 ]; then
  while getopts rklg:a:s:h OPT; do
    case $OPT in
    r)
      process="record"
      ;;
    p)
      process="provider"
      ;;
    l)
      process="liaison"
      ;;
    k)
      kill=true
      echo "Launch killer mode"
      ;;
    g)
      gcm=$OPTARG
      ;;
    a)
      pam=$OPTARG
      ;;
    s)
      sym=$OPTARG
      ;;
    h)
      echo "h option. display help" # for debug
      usage
      ;;
    \?)
      echo "Try to enter the h option." 1>&2
      ;;
    esac
  done
else
  echo "No installed getopts-command." 1>&2
  exit 1
fi

shift $((OPTIND - 1))

# source deactivate
# source activate py37
python_interpritor=python
execute_path=$(dirname $(pwd))
execute_path="${execute_path}/execute"
cd ${execute_path}
command="${python_interpritor} feedAgentController.py "
if [ "$process" == "liaison" ]; then
  if [ "${kill}" ]; then
    command="${command} --process ${process}"
  else
    command="${command} --process lkiller"
  if 
fi
if [ "$process" == "provider" ]; then
  if [ "${kill}" ]; then
    command="${command} --process ${process}"
  else
    command="${command} --process pkiller"
  if 
fi
if [ "$process" == "record" ]; then
  if [ "${kill}" ]; then
    command="${command} --process ${process}"
  else
    command="${command} --process rkiller"
  if 
fi

# general config
command="${command} --general_config_mode ${gcm}"
# private api
command="${command} --private_api_mode ${pam}"
# symbol
command="${command} --symbol ${sym}"

command="${command} "
echo $command
eval $command
