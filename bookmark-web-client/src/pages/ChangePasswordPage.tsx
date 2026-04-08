import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }
    setLoading(true);
    try {
      await api.changePassword(currentPassword, newPassword);
      setSuccess('Password updated successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card form-card">
        <h1 className="auth-title">
          <span className="logo-mark">◈</span> Change Password
        </h1>
        <form className="form-body" onSubmit={handleSubmit}>
          <div className="input-group">
            <label className="input-label" htmlFor="current-password">Current password</label>
            <input
              id="current-password"
              className="input-field"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <div className="input-group">
            <label className="input-label" htmlFor="new-password">New password</label>
            <input
              id="new-password"
              className="input-field"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </div>
          <div className="input-group">
            <label className="input-label" htmlFor="confirm-password">Confirm new password</label>
            <input
              id="confirm-password"
              className="input-field"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </div>
          {error && <p className="form-error">{error}</p>}
          {success && <p className="form-success">{success}</p>}
          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? <span className="btn-loading"><span className="spinner" /> Updating…</span> : 'Update password'}
          </button>
        </form>
        <p className="auth-link">
          <button className="btn-link" onClick={() => navigate('/')}>Back to bookmarks</button>
        </p>
      </div>
    </div>
  );
}
