/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */

// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  // By default, Docusaurus generates a sidebar from the docs folder structure
  // tutorialSidebar: [{type: 'autogenerated', dirName: '.'}],
  // But you can create a sidebar manually

  docsSidebar: [
    {
      type: 'doc',
      id: 'intro',
      label: 'Intoduction',
    },
    {
      type: 'category',
      label: 'Getting Started',
      link: {
        type: 'generated-index',
      },
      collapsed: false,
      items: [
        'getting-started/installation',
        'getting-started/quick-start',
        'getting-started/creating-bots',
      ],
    },
    {
      type: 'category',
      label: 'Tutorials',
      link: {
        type: 'generated-index',
      },
      collapsed: true,
      items: [
        'tutorials/restaurant',
        'tutorials/reservation',
        'tutorials/digressions',
      ],
    },
    {
      type: 'category',
      label: 'Design Guides',
      link: {
        type: 'generated-index',
      },
      collapsed: true,
      items: [
        'design-guides/channel-setting',
        'design-guides/dialog-tree',
        'design-guides/slot-filling',
        'design-guides/digressions',
        'design-guides/maxml',
        'design-guides/state',
        'design-guides/templates',
        'design-guides/subtrees',
        'design-guides/rpc',
        'design-guides/stories'
      ],
    },
    {
      type: 'category',
      label: 'Design Reference',
      link: {
        type: 'generated-index',
      },
      collapsed: true,
      items: [
        'design-reference/cli',
        'design-reference/resources',
        'design-reference/protocol',
        'design-reference/context',
        'design-reference/jinja',
        {
            type: 'category',
            label: 'Basic Types',
            collapsed: true,
            items: [
              'design-reference/strings',
              'design-reference/booleans',
              'design-reference/lists',
              'design-reference/dictionaries',
              'design-reference/numbers',
            ]
        },
        'design-reference/stories',
        'design-reference/timeout',
        'design-reference/pool-limits',
        'design-reference/timedelta',
        'design-reference/channels',
        'design-reference/mp',
      ],
    },
    {
      type: 'category',
      label: 'Extensions',
      link: {
        type: 'generated-index',
      },
      collapsed: true,
      items: [
        'extensions/datetime',
        'extensions/babel',
        'extensions/rasa',
        'extensions/jinja_loader',
        'extensions/rest',
      ],
    },
    {
      type: 'category',
      label: 'Coding Guides',
      link: {
        type: 'generated-index',
      },
      collapsed: true,
      items: [
        'coding-guides/basic-example',
        'coding-guides/bots',
        'coding-guides/resources',
        'coding-guides/channels',
        'coding-guides/extensions',
        'coding-guides/packaging',
        'coding-guides/maxml'
      ],
    },
  ],

};

module.exports = sidebars;
