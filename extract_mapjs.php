<?php

$mapFile = $argv[1];

if (!file_exists($mapFile)) {
    echo "Arquivo map '{$mapFile}' não encontrado.\n";
    exit(1);
}

$jsonContent = file_get_contents($mapFile);
$json = json_decode($jsonContent);
if (!$json) {
    echo "Erro ao decodificar o arquivo JSON.\n";
    exit(1);
}

if (!isset($json->sources) || !isset($json->sourcesContent)) {
    echo "O arquivo map não contém 'sources' ou 'sourcesContent'.\n";
    exit(1);
}

$extractedFiles = [];

foreach ($json->sources as $index => $source) {
    if (strpos($source, 'webpack://') === 0) {
        $source = substr($source, strlen('webpack://'));
    }
    $source = ltrim($source, '/');
    $dir = dirname($source);
    if (!is_dir($dir)) {
        if (!mkdir($dir, 0755, true)) {
            echo "Falha ao criar o diretório: {$dir}\n";
            continue;
        }
    }
    $fileName = basename($source);

    if (isset($json->sourcesContent[$index])) {
        $filePath = $dir . DIRECTORY_SEPARATOR . $fileName;
        if (file_put_contents($filePath, $json->sourcesContent[$index]) !== false) {
            $extractedFiles[] = $filePath;
        } else {
            echo "Erro ao gravar o arquivo: {$filePath}\n";
        }
    } else {
        echo "Conteúdo da fonte não encontrado para: {$source}\n";
    }
}

echo "Todos os códigos-fonte foram extraídos do arquivo map:\n";
print_r($extractedFiles);
