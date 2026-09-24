import AdminShell from '../../components/admin/admin-shell';
import styles from './page.module.css';

export default function AdminPage() {
  return (
    <AdminShell>
      <section className={styles.welcome}>
        <div>
          <p className={styles.kicker}>ADMINISTRATION</p>
          <h1>Good morning.</h1>
          <p>Your management workspace is ready for its first data-driven module.</p>
        </div>
        <span className={styles.badge}>Layout foundation</span>
      </section>

      <section className={styles.notice} aria-label="Implementation status">
        <span className={styles.noticeIcon}>i</span>
        <div><strong>Secure foundation in progress</strong><p>Admin data endpoints require server-side permissions. Dashboard metrics and management modules will be connected in their individual stages.</p></div>
      </section>

      <section className={styles.preview} aria-labelledby="workspace-heading">
        <div className={styles.heading}><div><p className={styles.kicker}>WORKSPACE</p><h2 id="workspace-heading">Module foundation</h2></div><span>PostgreSQL · FastAPI</span></div>
        <div className={styles.grid}>
          <article><span>01</span><h3>Identity</h3><p>Users, roles and permissions use normalized PostgreSQL models.</p><b>Ready</b></article>
          <article><span>02</span><h3>Authorization</h3><p>Every sensitive endpoint can declare its required permission.</p><b>Ready</b></article>
          <article><span>03</span><h3>Content</h3><p>Page and post management will be introduced in later stages.</p><b className={styles.pending}>Pending</b></article>
        </div>
      </section>
    </AdminShell>
  );
}
