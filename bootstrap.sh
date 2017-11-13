backup=$1
if [ $backup ]; then
    # taskwarrior
    mkdir -p backup
    mv $HOME/.task $HOME/.task.bak
    mkdir $HOME/.task
    ln -sf $backup/task/completed.data $HOME/.task/completed.data
    ln -sf $backup/task/pending.data $HOME/.task/pending.data
    ln -sf $PWD/taskwarrior/hooks $HOME/.task/hooks
    mv $HOME/.taskrc $HOME/.taskrc.bak
    echo "include $PWD/taskwarrior/taskrc
    context.work=project:ks +PROJECT
    context.home=project.not:ks +PROJECT" > $HOME/.taskrc

    # timewarrior
    mv $HOME/.timewarrior $HOME/.timewarrior.bak
    mkdir $HOME/.timewarrior
    ln -sf $backup/time $HOME/.timewarrior/data
    ln -sf $PWD/timewarrior/timewarrior.cfg $HOME/.timewarrior/timewarrior.cfg
    ln -sf $PWD/timewarrior/extensions $HOME/.timewarrior/extensions
else
	ln -s $PWD/taskwarrior/ $HOME/.task
	ln -s $PWD/timewarrior/ $HOME/.timewarrior
fi
