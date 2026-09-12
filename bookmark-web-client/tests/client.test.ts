import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from '../src/api/client'

function mockFetch(data: unknown, ok = true) {
  const fetchMock = vi.fn<typeof fetch>()
  fetchMock.mockResolvedValue({
    ok,
    json: async () => data,
  } as Response)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('API client', () => {
  it('builds bookmark filters and includes browser credentials', async () => {
    const bookmarks = [{ id: 1, url: 'https://example.test' }]
    const fetchMock = mockFetch(bookmarks)

    await expect(api.getBookmarks({
      search: 'fast api',
      tag: 'python',
      skip: 10,
      limit: 5,
    })).resolves.toEqual(bookmarks)

    const [url, options] = fetchMock.mock.calls[0]
    const requestURL = new URL(String(url))
    expect(`${requestURL.pathname}${requestURL.search}`).toBe(
      '/api/bookmarks?search=fast+api&tag=python&skip=10&limit=5',
    )
    expect(options).toEqual({
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    })
  })

  it('serializes authentication mutations', async () => {
    const fetchMock = mockFetch({ message: 'Password updated successfully' })

    await api.changePassword('current password', 'new password')

    const [url, options] = fetchMock.mock.calls[0]
    expect(new URL(String(url)).pathname).toBe('/api/auth/password')
    expect(options).toEqual({
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      method: 'PUT',
      body: JSON.stringify({
        current_password: 'current password',
        new_password: 'new password',
      }),
    })
  })

  it('surfaces API error details', async () => {
    mockFetch({ detail: 'Not authenticated' }, false)

    await expect(api.me()).rejects.toThrow('Not authenticated')
  })
})
