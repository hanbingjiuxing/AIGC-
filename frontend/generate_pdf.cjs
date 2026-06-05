var markdownpdf = require("markdown-pdf")
    , fs = require("fs")

var mdPath = "../SYSTEM_MANUAL.md"
var pdfPath = "../AIGC探索社信息系统说明书.pdf"

console.log("Starting PDF generation...")
markdownpdf()
    .from(mdPath)
    .to(pdfPath, function () {
        console.log("Done! PDF created at " + pdfPath)
    })
