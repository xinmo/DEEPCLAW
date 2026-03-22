import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

function getPackageName(id: string): string | null {
  const normalizedId = id.replace(/\\/g, '/')
  const nodeModulesIndex = normalizedId.lastIndexOf('/node_modules/')
  if (nodeModulesIndex === -1) {
    return null
  }

  const packagePath = normalizedId.slice(nodeModulesIndex + '/node_modules/'.length)
  const segments = packagePath.split('/')
  if (segments[0]?.startsWith('@')) {
    return segments.length >= 2 ? `${segments[0]}/${segments[1]}` : segments[0]
  }

  return segments[0] ?? null
}

function matchesPackage(packageName: string, patterns: string[]): boolean {
  return patterns.some((pattern) => {
    if (packageName === pattern || packageName.startsWith(`${pattern}/`)) {
      return true
    }
    if (pattern.endsWith('-')) {
      return packageName.startsWith(pattern)
    }
    return false
  })
}

function buildManualChunk(id: string): string | undefined {
  const packageName = getPackageName(id)
  if (!packageName) {
    return undefined
  }

  if (packageName === 'react' || packageName === 'react-dom' || packageName === 'scheduler') {
    return 'vendor-react'
  }

  if (
    matchesPackage(packageName, [
      'html2canvas',
    ])
  ) {
    return 'vendor-graph-export'
  }

  if (
    matchesPackage(packageName, [
      '@antv/g6',
      '@antv/g',
      '@antv/g-canvas',
      '@antv/g-lite',
      '@antv/component',
      '@antv/algorithm',
      '@antv/graphlib',
      '@antv/hierarchy',
      '@antv/layout',
      '@antv/scale',
      '@antv/util',
      'bubblesets-js',
      'd3-',
      'dagre',
      'gl-matrix',
      'graphlib',
      'is-any-array',
      'is-mobile',
      'ml-',
      'svg-path-parser',
      'vectorious',
    ])
  ) {
    return 'vendor-graph'
  }

  if (
    matchesPackage(packageName, [
      'react-markdown',
      'react-syntax-highlighter',
      'rehype-',
      'remark-',
      'hast-',
      'mdast-',
      'micromark',
      'micromark-',
      'parse5',
      'property-information',
      'entities',
      'unified',
      'unist-',
      'vfile',
      'vfile-',
      'space-separated-tokens',
      'comma-separated-tokens',
      'html-url-attributes',
      'html-void-elements',
      'decode-named-character-reference',
      'trim-lines',
      'web-namespaces',
      'zwitch',
      'bail',
      'devlop',
      'trough',
    ])
  ) {
    return 'vendor-markdown'
  }

  if (matchesPackage(packageName, ['docx-preview', 'jszip'])) {
    return 'vendor-docx'
  }

  if (packageName === 'lucide-react') {
    return 'vendor-icons'
  }

  if (packageName === 'axios') {
    return 'vendor-axios'
  }

  return undefined
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: buildManualChunk,
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
