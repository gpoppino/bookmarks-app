// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../src/api/client';
import { AuthProvider, useAuth } from '../src/context/AuthContext';
import type { User } from '../src/types';

vi.mock('../src/api/client', () => ({
  api: {
    me: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
  },
}));

const user: User = {
  id: 1,
  username: 'alice',
  created_at: '2026-09-14T10:00:00Z',
};

function AuthHarness() {
  const { user: currentUser, loading, login, logout, register } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="username">{currentUser?.username ?? 'anonymous'}</span>
      <button onClick={() => void login('alice', 'secret')}>login</button>
      <button onClick={() => void logout()}>logout</button>
      <button onClick={() => void register('alice', 'secret')}>register</button>
    </div>
  );
}

function renderAuth() {
  return render(
    <AuthProvider>
      <AuthHarness />
    </AuthProvider>,
  );
}

describe('AuthProvider', () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('restores an authenticated session during startup', async () => {
    vi.mocked(api.me).mockResolvedValue(user);

    renderAuth();

    expect(screen.getByTestId('loading').textContent).toBe('true');
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));
    expect(screen.getByTestId('username').textContent).toBe('alice');
  });

  it('finishes startup as anonymous when the session is invalid', async () => {
    vi.mocked(api.me).mockRejectedValue(new Error('Not authenticated'));

    renderAuth();

    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));
    expect(screen.getByTestId('username').textContent).toBe('anonymous');
  });

  it('updates authentication state after login and logout', async () => {
    vi.mocked(api.me).mockRejectedValue(new Error('Not authenticated'));
    vi.mocked(api.login).mockResolvedValue(user);
    vi.mocked(api.logout).mockResolvedValue({ success: true });
    renderAuth();
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));

    fireEvent.click(screen.getByText('login'));
    await waitFor(() => expect(screen.getByTestId('username').textContent).toBe('alice'));
    expect(api.login).toHaveBeenCalledWith({ username: 'alice', password: 'secret' });

    fireEvent.click(screen.getByText('logout'));
    await waitFor(() => expect(screen.getByTestId('username').textContent).toBe('anonymous'));
    expect(api.logout).toHaveBeenCalledOnce();
  });

  it('logs in after a successful registration', async () => {
    vi.mocked(api.me).mockRejectedValue(new Error('Not authenticated'));
    vi.mocked(api.register).mockResolvedValue(user);
    vi.mocked(api.login).mockResolvedValue(user);
    renderAuth();
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));

    fireEvent.click(screen.getByText('register'));

    await waitFor(() => expect(screen.getByTestId('username').textContent).toBe('alice'));
    expect(api.register).toHaveBeenCalledWith({ username: 'alice', password: 'secret' });
    expect(api.login).toHaveBeenCalledWith({ username: 'alice', password: 'secret' });
  });
});
