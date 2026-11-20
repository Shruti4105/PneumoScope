param([string]$Docx)
$ErrorActionPreference = "Stop"
$pdf = [IO.Path]::ChangeExtension($Docx, ".pdf")
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {
    $d = $w.Documents.Open($Docx, $false, $false, $false)
    $d.Repaginate()
    foreach ($t in $d.TablesOfContents) { $t.Update() }
    $d.Fields.Update() | Out-Null
    $d.Repaginate()
    foreach ($t in $d.TablesOfContents) { $t.Update() }
    "pages: " + $d.ComputeStatistics(2)
    "words: " + $d.ComputeStatistics(0)
    $d.Save()
    $d.ExportAsFixedFormat($pdf, 17, $false, 0, 0, 1, 1, 0, $true, $true, 1)
    $d.Close($false)
    "pdf: $pdf"
} finally { $w.Quit() }
