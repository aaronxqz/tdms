import { NavLink } from 'react-router-dom'

const links = [
  { to: '/',          label: 'Dashboard' },
  { to: '/waiting',   label: 'Waiting' },
  { to: '/assigned',  label: 'Assigned' },
  { to: '/search',    label: 'Search' },
  { to: '/goals',     label: 'Goals' },
]

export default function Navbar() {
  return (
    <nav style={{
      background: 'var(--surface)',
      borderBottom: '1px solid var(--border)',
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      gap: 4,
      height: 52,
    }}>
      <span style={{ fontWeight: 700, fontSize: 15, marginRight: 24, color: 'var(--accent)' }}>
        TDMS
      </span>
      {links.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          style={({ isActive }) => ({
            padding: '6px 14px',
            borderRadius: 6,
            color: isActive ? '#fff' : 'var(--text-muted)',
            background: isActive ? 'var(--accent)' : 'transparent',
            fontWeight: isActive ? 600 : 400,
            fontSize: 13,
            textDecoration: 'none',
            transition: 'all 0.15s',
          })}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
