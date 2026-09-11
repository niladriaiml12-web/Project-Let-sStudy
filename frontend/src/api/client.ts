import axios from 'axios'

// Axios instance — all requests go through /api proxy to FastAPI
const client = axios.create({
  baseURL: '/api/v1',
  timeout: 60000, // 60s for LLM calls
})

// Inject tenant headers on every request
client.interceptors.request.use((config) => {
  let apiKey = localStorage.getItem('study_api_key')
  const branch = localStorage.getItem('study_branch_code') || 'CSE_AIML'

  // If the user previously saved a Google API key in localStorage, reset it to the tenant key
  if (!apiKey || apiKey.startsWith('AQ.') || apiKey.startsWith('AIza') || !apiKey.startsWith('dev-key-')) {
    apiKey = branch === 'CSE_CORE' ? 'dev-key-cse-core-2026' : 'dev-key-cse-aiml-2026'
    localStorage.setItem('study_api_key', apiKey)
  }

  config.headers['X-API-Key'] = apiKey
  config.headers['X-Tenant-Branch'] = branch
  return config
})

export default client
