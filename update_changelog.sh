#!/bin/bash

# 更新changelog的脚本
# 检查main和dev分支的git log并更新changelog.md

CHANGELOG_FILE="changelog.md"
TEMP_LOG_FILE="/tmp/git_log_changes.txt"

# 获取当前日期
CURRENT_DATE=$(date +"%Y-%m-%d")

# 函数：获取分支的最新提交
get_branch_log() {
    local branch=$1
    local branch_name=$2
    
    # 切换到分支并获取最新的提交
    git checkout $branch >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "=== $branch_name 分支最新提交 ===" >> "$TEMP_LOG_FILE"
        git log --oneline --since="yesterday" --pretty=format:"%h - %s (%an, %ad)" --date=short >> "$TEMP_LOG_FILE" 2>/dev/null || echo "  无新提交" >> "$TEMP_LOG_FILE"
        echo "" >> "$TEMP_LOG_FILE"
    fi
}

# 清空临时文件
> "$TEMP_LOG_FILE"

# 添加标题
echo "# 更新日志 (自动生成)" > "$CHANGELOG_FILE"
echo "最后更新: $CURRENT_DATE" >> "$CHANGELOG_FILE"
echo "" >> "$CHANGELOG_FILE"

# 获取main分支日志
get_branch_log "main" "Main"

# 获取dev分支日志（如果存在）
if git show-ref --verify --quiet refs/heads/dev; then
    get_branch_log "dev" "Development"
else
    echo "=== Development 分支 ===" >> "$TEMP_LOG_FILE"
    echo "  分支不存在" >> "$TEMP_LOG_FILE"
    echo "" >> "$TEMP_LOG_FILE"
fi

# 如果有新内容，添加到changelog
if [ -s "$TEMP_LOG_FILE" ] && grep -v "无新提交\|分支不存在" "$TEMP_LOG_FILE" >/dev/null; then
    echo "## $CURRENT_DATE" >> "$CHANGELOG_FILE"
    cat "$TEMP_LOG_FILE" >> "$CHANGELOG_FILE"
    echo "" >> "$CHANGELOG_FILE"
    
    # 如果changelog已存在，保留历史记录
    if [ -f "$CHANGELOG_FILE.bak" ]; then
        tail -n +2 "$CHANGELOG_FILE.bak" >> "$CHANGELOG_FILE"
    fi
else
    echo "## $CURRENT_DATE" >> "$CHANGELOG_FILE"
    echo "无新的提交记录" >> "$CHANGELOG_FILE"
    echo "" >> "$CHANGELOG_FILE"
    
    # 如果changelog已存在，保留历史记录
    if [ -f "$CHANGELOG_FILE.bak" ]; then
        tail -n +2 "$CHANGELOG_FILE.bak" >> "$CHANGELOG_FILE"
    fi
fi

# 备份当前changelog
if [ -f "$CHANGELOG_FILE" ]; then
    cp "$CHANGELOG_FILE" "$CHANGELOG_FILE.bak"
fi

# 清理临时文件
rm -f "$TEMP_LOG_FILE"

# 返回到原来的分支
git checkout - >/dev/null 2>&1

echo "changelog.md 已更新 - $CURRENT_DATE"