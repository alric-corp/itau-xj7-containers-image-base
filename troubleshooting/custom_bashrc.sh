source /usr/share/bash-completion/bash_completion

source <(kubectl completion bash)
source <(helm completion bash)
source <(velero completion bash)

alias k=kubectl
complete -o default -F __start_kubectl k

complete -C '/usr/bin/aws_completer' aws
