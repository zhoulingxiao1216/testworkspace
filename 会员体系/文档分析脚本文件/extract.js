const fs = require('fs');
const path = require('path');

function extractLabels(htmlPath) {
    const html = fs.readFileSync(htmlPath, 'utf8');
    const fields = new Set();
    
    // Axure labels
    const axureLabels = html.matchAll(/data-label="([^"]+)"/gi);
    for (const match of axureLabels) {
        let text = match[1].trim();
        if (text && text.length < 30) fields.add('【元素】' + text);
    }
    
    // Axure Text spans
    const textSpans = html.matchAll(/<span[^>]*>([^<]+)<\/span>/gi);
    for (const match of textSpans) {
        let text = match[1].replace(/&nbsp;/g, '').replace(/&#8203;/g, '').trim();
        if (text && text.length < 20 && !text.match(/^[0-9a-fA-F-]+$/)) {
            fields.add(text);
        }
    }
    
    // Placeholders
    const placeholders = html.matchAll(/placeholder="([^"]+)"/gi);
    for (const match of placeholders) {
         if (match[1].trim()) fields.add('【占位符】' + match[1].trim());
    }

    // values
    const values = html.matchAll(/value="([^"]+)"/gi);
    for (const match of values) {
         if (match[1].trim() && match[1].trim().length < 20) fields.add('【值】' + match[1].trim());
    }

    return Array.from(fields);
}

const dirs = [
    'c:\\Users\\23282\\Desktop\\AI\\项目\\global-v2\\docs\\pm\\会员体系管理端',
    'c:\\Users\\23282\\Desktop\\AI\\项目\\global-v2\\docs\\pm\\会员体系用户端'
];

const result = {};

dirs.forEach(dir => {
    if (fs.existsSync(dir)) {
        fs.readdirSync(dir).forEach(file => {
            if (file.endsWith('.html') && !file.includes('start.html')) {
                const fields = extractLabels(path.join(dir, file));
                const uniqueFields = fields.filter((item, pos) => fields.indexOf(item) === pos);
                // Clean up garbage
                const cleanFields = uniqueFields.filter(f => f.length > 1 && !f.includes('{') && !f.includes('font-family'));
                result[file] = cleanFields;
            }
        });
    }
});

fs.writeFileSync('c:\\Users\\23282\\Desktop\\AI\\项目\\global-v2\\docs\\pm\\fields.json', JSON.stringify(result, null, 2));
