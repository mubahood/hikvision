#!/usr/bin/env python3
"""
Generate PDF documentation for EHRMS Portal Device Bridge
"""

from fpdf import FPDF


class BridgeDocPDF(FPDF):
    BRAND = (121, 13, 11)       # #790D0B
    BRAND_LIGHT = (121, 13, 11, 40)
    WHITE = (255, 255, 255)
    DARK = (40, 40, 40)
    GRAY = (100, 100, 100)
    LIGHT_BG = (248, 245, 245)
    ACCENT_LINE = (121, 13, 11)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*self.BRAND)
        self.rect(0, 0, 210, 2.5, 'F')
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*self.GRAY)
        self.set_y(5)
        self.cell(0, 5, 'EHRMS Portal - Device Bridge Documentation', align='R')
        self.ln(10)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_fill_color(*self.BRAND)
        self.rect(0, self.h - 3, 210, 3, 'F')
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*self.GRAY)
        self.cell(0, 10, f'Page {self.page_no() - 1}', align='C')

    def cover_page(self):
        self.add_page()
        # Full brand colour top block
        self.set_fill_color(*self.BRAND)
        self.rect(0, 0, 210, 145, 'F')

        # University title
        self.set_text_color(*self.WHITE)
        self.set_font('Helvetica', 'B', 32)
        self.set_y(38)
        self.cell(0, 14, 'Mountains of the Moon', align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_font('Helvetica', '', 26)
        self.cell(0, 12, 'University', align='C', new_x="LMARGIN", new_y="NEXT")

        # Divider line
        self.set_draw_color(*self.WHITE)
        self.set_line_width(0.6)
        self.line(60, 75, 150, 75)

        # Subtitle
        self.set_font('Helvetica', 'B', 18)
        self.set_y(82)
        self.cell(0, 10, 'EHRMS Portal', align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_font('Helvetica', '', 15)
        self.cell(0, 9, 'Device Bridge', align='C', new_x="LMARGIN", new_y="NEXT")

        # Tagline
        self.set_font('Helvetica', 'I', 11)
        self.set_y(110)
        self.cell(0, 8, 'Hikvision DS-K1T680 Face Recognition Terminal Integration', align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_font('Helvetica', '', 10)
        self.cell(0, 7, 'Installation & Setup Guide', align='C', new_x="LMARGIN", new_y="NEXT")

        # Bottom white section
        self.set_text_color(*self.DARK)
        self.set_font('Helvetica', '', 10)
        self.set_y(155)
        self.cell(0, 7, 'Version 1.0', align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*self.GRAY)
        self.set_font('Helvetica', '', 9)
        self.cell(0, 6, 'March 2026', align='C', new_x="LMARGIN", new_y="NEXT")

        # Architecture mini-diagram label
        self.set_y(185)
        self.set_text_color(*self.BRAND)
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 6, 'System Overview', align='C', new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(*self.GRAY)
        self.set_font('Courier', '', 8)
        arch_lines = [
            'Hikvision Device  --[ISAPI Polling]-->  Python Bridge  --[Webhook]--> EHRMS Backend',
            '                                             |',
            '                                      MySQL + Dashboard',
        ]
        for line in arch_lines:
            self.cell(0, 5, line, align='C', new_x="LMARGIN", new_y="NEXT")

        # Confidential footer
        self.set_y(260)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*self.GRAY)
        self.cell(0, 5, 'Mountains of the Moon University  |  IT Department  |  Confidential', align='C')

    def section_title(self, num, title):
        self.ln(4)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(*self.BRAND)
        self.cell(0, 10, f'{num}.  {title}', new_x="LMARGIN", new_y="NEXT")
        # underline
        self.set_draw_color(*self.BRAND)
        self.set_line_width(0.5)
        y = self.get_y()
        self.line(self.l_margin, y, 120, y)
        self.ln(4)

    def sub_title(self, title):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(*self.DARK)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*self.DARK)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def code_block(self, code):
        self.set_fill_color(42, 42, 42)
        self.set_text_color(220, 220, 210)
        self.set_font('Courier', '', 9)
        x = self.get_x()
        y = self.get_y()
        lines = code.strip().split('\n')
        block_h = len(lines) * 5.5 + 6
        self.rect(x, y, 190 - self.l_margin, block_h, 'F')
        self.set_xy(x + 4, y + 3)
        for line in lines:
            self.cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")
            self.set_x(x + 4)
        self.ln(4)
        self.set_text_color(*self.DARK)

    def bullet(self, text, indent=10):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*self.DARK)
        x = self.get_x()
        self.set_x(x + indent)
        # bullet dot
        self.set_fill_color(*self.BRAND)
        self.ellipse(x + indent, self.get_y() + 2, 2, 2, 'F')
        self.set_x(x + indent + 5)
        self.multi_cell(170 - indent, 5.5, text)
        self.ln(1)

    def env_row(self, key, desc, example):
        self.set_font('Courier', 'B', 9)
        self.set_text_color(*self.BRAND)
        self.cell(50, 5.5, key)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(*self.DARK)
        self.cell(70, 5.5, desc)
        self.set_font('Courier', '', 9)
        self.set_text_color(*self.GRAY)
        self.cell(0, 5.5, example, new_x="LMARGIN", new_y="NEXT")

    def table_header(self, cols, widths):
        self.set_fill_color(*self.BRAND)
        self.set_text_color(*self.WHITE)
        self.set_font('Helvetica', 'B', 9)
        for col, w in zip(cols, widths):
            self.cell(w, 7, f'  {col}', fill=True)
        self.ln()
        self.set_text_color(*self.DARK)

    def table_row(self, cols, widths, fill=False):
        if fill:
            self.set_fill_color(*self.LIGHT_BG)
        self.set_font('Helvetica', '', 9)
        for col, w in zip(cols, widths):
            self.cell(w, 6.5, f'  {col}', fill=fill)
        self.ln()


def build_pdf():
    pdf = BridgeDocPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Cover ──
    pdf.cover_page()

    # ── Page: Table of Contents ──
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*pdf.BRAND)
    pdf.cell(0, 12, 'Table of Contents', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    toc = [
        ('1', 'Prerequisites', '3'),
        ('2', 'Installation', '3'),
        ('3', 'Configuration', '4'),
        ('4', 'Database Setup', '5'),
        ('5', 'Running the System', '5'),
        ('6', 'Dashboard', '6'),
        ('7', 'Desktop Manager App', '7'),
        ('8', 'Management Commands', '8'),
        ('9', 'Project Structure', '8'),
        ('10', 'Troubleshooting & FAQ', '9'),
    ]
    for num, title, page in toc:
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(*pdf.DARK)
        pdf.cell(8, 8, num + '.')
        pdf.cell(140, 8, title)
        pdf.set_text_color(*pdf.GRAY)
        pdf.cell(0, 8, page, align='R', new_x="LMARGIN", new_y="NEXT")

    # ── Section 1: Prerequisites ──
    pdf.add_page()
    pdf.section_title('1', 'Prerequisites')
    pdf.body_text('Ensure the following are installed on your server or local machine before proceeding:')

    pdf.bullet('Python 3.10 or higher')
    pdf.bullet('MySQL 5.7+ or MariaDB 10.3+')
    pdf.bullet('pip (Python package manager)')
    pdf.bullet('Git (for cloning the repository)')
    pdf.bullet('Hikvision DS-K1T680 terminal accessible on the same network')

    pdf.ln(3)
    pdf.sub_title('Verify Python')
    pdf.code_block('python3 --version\n# Expected: Python 3.10+')

    pdf.sub_title('Verify MySQL')
    pdf.code_block('mysql --version\n# Expected: mysql Ver 8.x or MariaDB 10.x')

    # ── Section 2: Installation ──
    pdf.section_title('2', 'Installation')

    pdf.sub_title('Step 1 - Clone the Repository')
    pdf.code_block('git clone https://github.com/your-org/ehrms-device-bridge.git\ncd ehrms-device-bridge')

    pdf.sub_title('Step 2 - Create Virtual Environment')
    pdf.code_block('python3 -m venv .venv\nsource .venv/bin/activate    # Linux / macOS\n# .venv\\Scripts\\activate     # Windows')

    pdf.sub_title('Step 3 - Install Dependencies')
    pdf.code_block('pip install -r requirements.txt')

    pdf.ln(2)
    pdf.body_text('Installed packages include: requests, python-dotenv, mysql-connector-python, streamlit, pandas, and plotly.')

    # ── Section 3: Configuration ──
    pdf.add_page()
    pdf.section_title('3', 'Configuration')
    pdf.body_text('Copy the environment template and edit it with your specific settings:')
    pdf.code_block('cp .env.example .env\nnano .env          # or use any text editor')

    pdf.ln(2)
    pdf.sub_title('Environment Variables')
    pdf.ln(2)

    widths = [50, 70, 60]
    pdf.table_header(['Variable', 'Description', 'Example'], widths)
    rows = [
        ('DEVICE_IP', 'Hikvision device IP', '192.168.1.128'),
        ('DEVICE_USER', 'Device admin username', 'admin'),
        ('DEVICE_PASS', 'Device admin password', 'your_password'),
        ('DEVICE_ID', 'Unique device identifier', '192.168.1.128'),
        ('POLL_INTERVAL', 'Polling frequency (seconds)', '2'),
        ('BATCH_SIZE', 'Max events per poll', '30'),
        ('DB_HOST', 'MySQL host', 'localhost'),
        ('DB_PORT', 'MySQL port', '3306'),
        ('DB_USER', 'MySQL username', 'root'),
        ('DB_PASS', 'MySQL password', 'root'),
        ('DB_NAME', 'Database name', 'hikvision'),
        ('LOG_LEVEL', 'Logging verbosity', 'INFO'),
        ('LOG_FILE', 'Log output file', 'hikvision_bridge.log'),
    ]
    for i, (var, desc, ex) in enumerate(rows):
        pdf.table_row([var, desc, ex], widths, fill=(i % 2 == 0))

    # ── Section 4: Database Setup ──
    pdf.add_page()
    pdf.section_title('4', 'Database Setup')
    pdf.body_text('Create the database and required tables using the provided SQL script:')

    pdf.sub_title('Step 1 - Create the Database')
    pdf.code_block('mysql -u root -p\nCREATE DATABASE hikvision;\nEXIT;')

    pdf.sub_title('Step 2 - Import Tables')
    pdf.code_block('mysql -u root -p < create_tables.sql')

    pdf.ln(2)
    pdf.body_text('This creates the events table, bridge_status table, and all necessary indexes for optimal performance.')

    # ── Section 5: Running the System ──
    pdf.section_title('5', 'Running the System')

    pdf.sub_title('Option A - Quick Start (Recommended)')
    pdf.body_text('Use the bundled start script to launch both the bridge and dashboard:')
    pdf.code_block('./start.sh')
    pdf.body_text('This will automatically create a virtual environment, install dependencies, and start both services in the background.')

    pdf.sub_title('Option B - Manual Start')
    pdf.body_text('Run each component in a separate terminal:')

    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(*pdf.GRAY)
    pdf.cell(0, 6, 'Terminal 1 - Bridge Service', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block('source .venv/bin/activate\npython hikvision_bridge.py')

    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(*pdf.GRAY)
    pdf.cell(0, 6, 'Terminal 2 - Dashboard', new_x="LMARGIN", new_y="NEXT")
    pdf.code_block('source .venv/bin/activate\nstreamlit run dashboard.py --server.port 8502')

    # ── Section 6: Dashboard ──
    pdf.add_page()
    pdf.section_title('6', 'Dashboard')
    pdf.body_text('The Streamlit dashboard provides a real-time web interface to monitor and manage the bridge.')

    pdf.sub_title('Access')
    pdf.code_block('http://localhost:8502')

    pdf.ln(2)
    pdf.sub_title('Features')
    pdf.bullet('Live event monitoring with auto-refresh')
    pdf.bullet('Event statistics and charts (Plotly)')
    pdf.bullet('Manual device sync (up to 1000 historical events)')
    pdf.bullet('Batch upload pending/failed events to webhook')
    pdf.bullet('Start/stop bridge process from the UI')
    pdf.bullet('Filter events by date, employee, door, and status')

    # ── Section 7: Desktop Manager App ──
    pdf.add_page()
    pdf.section_title('7', 'Desktop Manager App')
    pdf.body_text(
        'The EHRMS Device Bridge includes a native cross-platform desktop application '
        'built with C# and Avalonia UI. This manager provides a graphical interface '
        'for setup, configuration, monitoring, and control of the bridge system - '
        'no command-line knowledge required.'
    )

    pdf.sub_title('Key Features')
    pdf.bullet('Home Dashboard - Real-time overview of system status (Python, venv, config, bridge, dashboard)')
    pdf.bullet('Setup Wizard - 6-step guided installation: Python check, virtual environment, dependencies, config, DB test, device test')
    pdf.bullet('Settings - Visual editor for all .env configuration variables (device, database, webhook, bridge)')
    pdf.bullet('Run Services - Start/stop bridge and dashboard with one click, status indicators, open dashboard in browser')
    pdf.bullet('Diagnostics - Automated health checks and connection testing')
    pdf.bullet('Log Viewer - Built-in dark-themed log viewer for bridge and dashboard logs')
    pdf.bullet('User Guide - In-app documentation and quick reference')

    pdf.ln(3)
    pdf.sub_title('How to Use')
    pdf.body_text(
        'Place the executable (EHRMSBridgeApp.exe on Windows, or EHRMSBridgeApp on macOS) '
        'in the same directory as the bridge project, or any parent directory. '
        'The app automatically locates the hikvision_bridge.py file.'
    )

    pdf.sub_title('Available Builds')
    pdf.ln(2)
    widths_builds = [60, 120]
    pdf.table_header(['Platform', 'File'], widths_builds)
    pdf.table_row(['Windows x64', 'EHRMSBridgeApp.exe (92 MB)'], widths_builds, fill=True)
    pdf.table_row(['macOS ARM64', 'EHRMSBridgeApp (102 MB)'], widths_builds, fill=False)

    pdf.ln(4)
    pdf.sub_title('Error Handling')
    pdf.body_text(
        'The desktop app is production-hardened with comprehensive error handling. '
        'All operations are wrapped in try/catch blocks with user-friendly error messages. '
        'Unhandled exceptions are logged to crash.log in the application directory. '
        'The app will never crash silently - all errors are reported in the UI.'
    )

    # ── Section 8: Management Commands ──
    pdf.section_title('8', 'Management Commands')
    pdf.body_text('Use the provided shell scripts to manage the system:')

    pdf.ln(2)
    widths2 = [55, 125]
    pdf.table_header(['Command', 'Description'], widths2)
    cmds = [
        ('./start.sh', 'Start bridge + dashboard (creates venv if needed)'),
        ('./stop.sh', 'Stop all running processes'),
        ('./status.sh', 'Show running status of bridge and dashboard'),
        ('python hikvision_bridge.py', 'Run bridge in foreground (manual mode)'),
        ('streamlit run dashboard.py', 'Run dashboard standalone'),
    ]
    for i, (cmd, desc) in enumerate(cmds):
        pdf.table_row([cmd, desc], widths2, fill=(i % 2 == 0))

    # ── Section 9: Project Structure ──
    pdf.add_page()
    pdf.section_title('9', 'Project Structure')
    pdf.code_block(
        'ehrms-device-bridge/\n'
        '  hikvision_bridge.py      # Main bridge service\n'
        '  dashboard.py             # Streamlit dashboard\n'
        '  database.py              # MySQL connection & queries\n'
        '  create_tables.sql        # Database schema\n'
        '  requirements.txt         # Python dependencies\n'
        '  .env                     # Environment config (create from .env.example)\n'
        '  start.sh                 # Start all services\n'
        '  stop.sh                  # Stop all services\n'
        '  status.sh                # Check service status\n'
        '  controllers/             # API & logic controllers\n'
        '  models/                  # Data models\n'
        '  data/                    # JSON event backups (by date)\n'
        '  installer/               # Desktop manager app (C# / Avalonia UI)'
    )

    # ── Section 10: Troubleshooting & FAQ ──
    pdf.section_title('10', 'Troubleshooting & FAQ')

    issues = [
        ('Bridge fails to start',
         'Check .env file exists and has correct DEVICE_IP, DEVICE_USER, DEVICE_PASS. '
         'Verify the Hikvision device is reachable: ping <DEVICE_IP>.'),
        ('Database connection error',
         'Confirm MySQL is running. Verify DB_HOST, DB_PORT, DB_USER, DB_PASS in .env. '
         'Ensure the "hikvision" database exists.'),
        ('Dashboard not loading',
         'Make sure port 8502 is not in use. Check dashboard.log for errors.'),
        ('Events not syncing to webhook',
         'Check WEBHOOK_URL in .env. Review bridge_output.log for HTTP errors. '
         'Use the dashboard to retry failed events.'),
        ('Permission denied on scripts',
         'Run: chmod +x start.sh stop.sh status.sh'),
        ('Desktop app cannot find project',
         'Place the executable in the same directory as hikvision_bridge.py, or a parent '
         'directory. The app searches upward from its location to find the project.'),
        ('Desktop app shows "Python not found"',
         'Install Python 3.10+ and ensure it is in your system PATH. Restart the app after installing.'),
    ]

    for title, fix in issues:
        pdf.set_fill_color(*pdf.LIGHT_BG)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*pdf.BRAND)
        y = pdf.get_y()
        pdf.rect(pdf.l_margin, y, 180, 6.5, 'F')
        pdf.cell(0, 6.5, f'  {title}', new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*pdf.DARK)
        pdf.set_font('Helvetica', '', 9.5)
        pdf.set_x(pdf.l_margin + 3)
        pdf.multi_cell(174, 5, fix)
        pdf.ln(3)

    # FAQ section
    pdf.ln(4)
    pdf.sub_title('Frequently Asked Questions')

    faqs = [
        ('Does the desktop app need .NET installed?',
         'No. The published executable is self-contained and includes the .NET runtime. No additional installation is needed.'),
        ('Can I run the bridge on a server without the desktop app?',
         'Yes. The bridge is a Python script that runs independently. Use ./start.sh or run hikvision_bridge.py directly.'),
        ('How do I update the bridge?',
         'Pull the latest code from the repository, then re-run pip install -r requirements.txt inside the virtual environment.'),
        ('What ports does the system use?',
         'Port 8502 for the Streamlit dashboard. The bridge communicates with the Hikvision device on its configured IP (typically port 80).'),
        ('Is the data backed up?',
         'Yes. Events are stored in MySQL AND as daily JSON files in the data/ directory.'),
    ]

    for q, a in faqs:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*pdf.BRAND)
        pdf.cell(0, 6, f'Q: {q}', new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*pdf.DARK)
        pdf.set_font('Helvetica', '', 9.5)
        pdf.set_x(pdf.l_margin + 3)
        pdf.multi_cell(174, 5, f'A: {a}')
        pdf.ln(2)

    # ── Final Page ──
    pdf.add_page()
    pdf.ln(50)
    pdf.set_fill_color(*pdf.BRAND)
    pdf.rect(30, pdf.get_y(), 150, 0.8, 'F')
    pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*pdf.BRAND)
    pdf.cell(0, 12, 'Mountains of the Moon University', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 13)
    pdf.set_text_color(*pdf.DARK)
    pdf.cell(0, 8, 'EHRMS Portal - Device Bridge', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(*pdf.GRAY)
    pdf.cell(0, 6, 'For support, contact the IT Department.', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, 'Document generated March 2026.', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_fill_color(*pdf.BRAND)
    pdf.rect(30, pdf.get_y(), 150, 0.8, 'F')

    # ── Save ──
    output_path = 'EHRMS_Device_Bridge_Documentation.pdf'
    pdf.output(output_path)
    print(f'\n  PDF generated: {output_path}\n')


if __name__ == '__main__':
    build_pdf()
