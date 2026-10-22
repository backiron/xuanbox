import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Links in rendered Markdown open in a new tab and never get access to this page.
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A' && node.getAttribute('href')) {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})

export function renderMarkdown(source) {
  return DOMPurify.sanitize(marked.parse(source || '', { gfm: true, breaks: true }))
}
