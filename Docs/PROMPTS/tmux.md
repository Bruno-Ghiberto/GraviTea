## 1. Pre-Launch Steps

### 1.1 Set Environment Variable

```bash
# INITIATE SESSION IN ONE LINER COMMAND (Fixed: detached mode + proper config)
cd ~/Documents/Projects/GraviTea && \
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 && \
tmux has-session -t GraviTea 2>/dev/null || \
  tmux new-session -d -s GraviTea -x 240 -y 60 && \
tmux set-option -t GraviTea -g mouse on && \
tmux set-option -t GraviTea -g history-limit 50000 && \
tmux set-option -t GraviTea -g pane-border-status top && \
tmux set-option -t GraviTea -g pane-border-format " #{pane_index}: #{pane_title} " && \
tmux set-option -t GraviTea -g pane-border-style "fg=colour240" && \
tmux set-option -t GraviTea -g pane-active-border-style "fg=colour75,bold" && \
tmux set-option -t GraviTea -g status-right "#{pane_title} | %H:%M" && \
tmux set-option -t GraviTea -g status-interval 5 && \
tmux set-option -t GraviTea -g display-panes-time 3000 && \
tmux set-option -t GraviTea -g pane-base-index 1 && \
tmux set-option -t GraviTea -g base-index 1 && \
tmux set-option -t GraviTea -g remain-on-exit off && \
tmux attach-session -t GraviTea

# REQUIRED — enables Agent Teams multi-pane coordination
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```