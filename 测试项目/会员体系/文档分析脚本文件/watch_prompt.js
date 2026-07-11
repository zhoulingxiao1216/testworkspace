const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, '..', 'PRD提示词文档.md');

function formatMarkdown(content) {
    let newContent = content;

    // 1. 中文接英文/数字加空格
    newContent = newContent.replace(/([\u4e00-\u9fa5])([a-zA-Z0-9])/g, '$1 $2');
    
    // 2. 英文/数字接中文加空格
    newContent = newContent.replace(/([a-zA-Z0-9])([\u4e00-\u9fa5])/g, '$1 $2');
    
    // 3. 标题行格式化 (除了第一行，其它带 # 的标题前面保证空两行)
    newContent = newContent.replace(/([^\n])\n(#+ )/g, '$1\n\n$2');
    
    // 4. 标准化代码块
    newContent = newContent.replace(/``` markdown/g, '```markdown');
    
    // 5. 压缩连续多行为两行
    newContent = newContent.replace(/\n{3,}/g, '\n\n');

    return newContent;
}

console.log('==================================================');
console.log('👀 AI 自动化守护脚本已启动！');
console.log(`正在实时监听：${path.basename(filePath)}`);
console.log('功能：当您修改文件并保存时，自动执行中英版面整理、标题间距规整等工作。');
console.log('按下 Ctrl+C 即可退出');
console.log('==================================================\n');

if (!fs.existsSync(filePath)) {
    console.error(`❌ 错误：找不到文件 ${filePath}！`);
    process.exit(1);
}

let fsWait = false;
fs.watch(filePath, (event, filename) => {
    if (filename && event === 'change') {
        if (fsWait) return;
        fsWait = setTimeout(() => {
            fsWait = false;
        }, 500); // 节流控制，防止编辑器多次触发保存事件

        console.log(`[${new Date().toLocaleTimeString()}] ✍️ 检测到内容变动，正在自动排版...`);

        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            const newContent = formatMarkdown(content);

            if (content !== newContent) {
                fs.writeFileSync(filePath, newContent, 'utf-8');
                console.log(`[${new Date().toLocaleTimeString()}] ✅ 整理完成：已完成中英混排打磨和 MD 格式美化！\n`);
            } else {
                console.log(`[${new Date().toLocaleTimeString()}] ⚡ 整理完毕：当前格式已处于完美状态，无需修改。\n`);
            }
        } catch (e) {
            console.log(`[${new Date().toLocaleTimeString()}] ⚠️ 整理冲突，可能文件锁定: ${e.message}`);
        }
    }
});
