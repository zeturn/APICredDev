const config = {
  title: 'APICred Docs',
  tagline: 'APICred documentation site',
  url: 'https://example.com',
  baseUrl: '/APICred/',
  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',
  favicon: 'data:;base64,iVBORw0KGgo=',
  organizationName: 'example',
  projectName: 'APICred',
  i18n: {
    defaultLocale: 'zh-Hans',
    locales: ['zh-Hans', 'en']
  },
  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.js',
          routeBasePath: '/'
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css'
        }
      }
    ]
  ],
  themeConfig: {
    navbar: {
      title: 'APICred Docs',
      items: [{ type: 'docSidebar', sidebarId: 'tutorialSidebar', position: 'left', label: 'Docs' }]
    },
    footer: {
      style: 'dark',
      copyright: `Copyright © ${new Date().getFullYear()} APICred`
    }
  }
};

module.exports = config;
