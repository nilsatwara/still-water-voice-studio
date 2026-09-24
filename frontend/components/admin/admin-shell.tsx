'use client';

import type { ReactNode } from 'react';
import { useState } from 'react';
import { usePathname } from 'next/navigation';
import styles from './admin-shell.module.css';

const navigation = [
  { label: 'Overview', items: [['Dashboard', '⌂']] },
  { label: 'Content', items: [['Pages', '□'], ['Posts', '≡'], ['Categories', '◇'], ['Tags', '#'], ['Media', '▧'], ['Menus', '☷']] },
  { label: 'TTS', items: [['Engines', '⌁'], ['Voices', '◉'], ['Languages', '◎'], ['Generations', '▷'], ['Cache', '↻'], ['Usage limits', '◫']] },
  { label: 'Users', items: [['All users', '♙'], ['Free users', '○'], ['Pro users', '◆'], ['Trial users', '◷'], ['Roles', '♧'], ['Permissions', '⌘']] },
  { label: 'Monetization', items: [['Plans', '▤'], ['Advertisements', '▣'], ['Payment gateways', '◇'], ['Payments', '¤'], ['Refunds', '↩']] },
  { label: 'Developer', items: [['API keys', '⌑'], ['API usage', '⌇'], ['API settings', '⚙']] },
  { label: 'Communication', items: [['Contact messages', '✉'], ['Email templates', '▱']] },
  { label: 'Settings', items: [['General', '⚙'], ['Branding', '✦'], ['SEO', '⌕'], ['Social', '◎'], ['Email', '@'], ['CAPTCHA', '✓'], ['Security', '◈'], ['Cache', '↻'], ['TTS settings', '⌁'], ['Limits', '◫']] },
  { label: 'System', items: [['Audit logs', '▥'], ['Security events', '!'], ['Backup / Git', '⑂']] },
] as const;

export default function AdminShell({ children }: Readonly<{ children: ReactNode }>) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return <div className={styles.adminRoot}>
    <aside className={`${styles.sidebar} ${open ? styles.open : ''}`} aria-label="Administration navigation">
      <div className={styles.sideTop}>
        <a className={styles.brand} href="/"><span>≋</span><strong>stillwater<small>ADMINISTRATION</small></strong></a>
        <button className={styles.close} onClick={() => setOpen(false)} aria-label="Close navigation">×</button>
      </div>
      <nav>{navigation.map((group, groupIndex) => <section className={styles.navGroup} key={group.label}>
        <h2>{group.label}</h2>
        {group.items.map(([item, icon], itemIndex) => { const contentRoutes=['/admin/pages/','/admin/posts/','/admin/categories/','/admin/tags/','/admin/media/','/admin/menus/']; const href=groupIndex===0&&itemIndex===0?'/admin/':groupIndex===1&&itemIndex<6?contentRoutes[itemIndex]:groupIndex===7&&itemIndex===0?'/admin/settings/general/':groupIndex===7&&itemIndex===5?'/admin/settings/captcha/':'#'; const active=pathname===href||pathname===href.slice(0,-1); return <a
          href={href}
          aria-current={active ? 'page' : undefined}
          aria-disabled={href === '#'}
          className={active ? styles.active : styles.future}
          key={item}
        ><span>{icon}</span>{item}{item === 'Security events' && <i>0</i>}</a>})}
      </section>)}</nav>
      <div className={styles.sideFooter}><span>N</span><div><strong>Nilesh</strong><small>Administrator</small></div><button aria-label="Profile options">•••</button></div>
    </aside>
    {open && <button className={styles.scrim} onClick={() => setOpen(false)} aria-label="Close navigation overlay" />}

    <div className={styles.mainColumn}>
      <header className={styles.topbar}>
        <button className={styles.menu} onClick={() => setOpen(true)} aria-label="Open navigation">☰</button>
        <div className={styles.crumbs}><a href="/admin/">Admin</a><span>/</span><strong>Dashboard</strong></div>
        <label className={styles.search}><span>⌕</span><input placeholder="Search administration" aria-label="Search administration" disabled /></label>
        <div className={styles.actions}><a href="/" title="View site" aria-label="View site">↗</a><button title="Notifications" aria-label="Notifications">♢<i /></button><button className={styles.profile} title="Profile menu" aria-label="Profile menu">N</button></div>
      </header>
      <main className={styles.workspace}>{children}</main>
    </div>
  </div>;
}
