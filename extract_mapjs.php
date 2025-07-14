<?php

$mapFile = $argv[1] ?? null;

if (!$mapFile || !file_exists($mapFile)) {
    fwrite(STDERR, "Arquivo map '{$mapFile}' não encontrado.\n");
    exit(1);
}

$jsonContent = file_get_contents($mapFile);
$json = json_decode($jsonContent);
if (!$json) {
    fwrite(STDERR, "Erro ao decodificar o arquivo JSON.\n");
    exit(1);
}

if (!isset($json->sources) || !isset($json->sourcesContent)) {
    fwrite(STDERR, "O arquivo map não contém 'sources' ou 'sourcesContent'.\n");
    exit(1);
}

$extractedFiles = [];

foreach ($json->sources as $index => $source) {
    // Remover prefixo webpack://
    if (strpos($source, 'webpack://') === 0) {
        $source = substr($source, strlen('webpack://'));
    }
    // Remover barras iniciais
    $source = ltrim($source, '/\\');
    // Evitar diretórios acima (../ ou ..\)
    $safeSource = str_replace(['../', '..\\'], '', $source);
    // Normalize para diretório atual
    $safeSource = trim($safeSource, "/\\");

    $dir = dirname($safeSource);
    $fileName = basename($safeSource);

    // Se dirname retornar '.', significa diretório atual
    if ($dir !== '.' && $dir !== '' && !is_dir($dir)) {
        if (!mkdir($dir, 0755, true)) {
            fwrite(STDERR, "Falha ao criar o diretório: {$dir}\n");
            continue;
        }
    }

    $filePath = ($dir !== '.' && $dir !== '' ? $dir . DIRECTORY_SEPARATOR : '') . $fileName;

    if (isset($json->sourcesContent[$index])) {
        if (file_put_contents($filePath, $json->sourcesContent[$index]) !== false) {
            $extractedFiles[] = $filePath;
        } else {
            fwrite(STDERR, "Erro ao gravar o arquivo: {$filePath}\n");
        }
    } else {
        fwrite(STDERR, "Conteúdo da fonte não encontrado para: {$safeSource}\n");
    }
}

echo "Todos os códigos-fonte foram extraídos no diretório atual:\n";
print_r($extractedFiles);
