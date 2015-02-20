module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    sass: {
      options: {
        sourcemap: true,
        style: "compressed"
      },
      dist: {
          files: [{
            expand: true,
            cwd: 'static/sass',
            src: ['*.sass'],
            dest: 'static/css',
            ext: '.css'
          }]
      }
    },
    concat: {
      app: {
        src: [
          'static/js/app.js',
          'static/js/controllers.js',
          'static/js/services.js',
          'static/js/filters.js',
          'static/js/directives.js',
          'static/dist/js/templates.js',
          '../proso_feedback/static/js/app.js',
          '../proso_feedback/static/js/app.js',
          '../proso_user/static/js/app.js',
          '../proso_user/static/dist/js/templates.js',
        ],
        dest: 'static/dist/js/<%= pkg.name %>.min.js'
      },
    },
    shell: {
        runserver: {
            command: './manage.py runserver'
        }
    },
    ngtemplates:    {
      adaptivePractice:          {
        src: [
          'static/tpl/*.html',
        ],
        dest: 'static/dist/js/templates.js',
        options:    {
          htmlmin:  { collapseWhitespace: true, collapseBooleanAttributes: true }
        }
      },
      'proso.feedback':          {
        cwd: '../proso_feedback',
        src: [
          'static/tpl/*.html',
        ],
        dest: '../proso_feedback/static/dist/js/templates.js',
        options:    {
          htmlmin:  { collapseWhitespace: true, collapseBooleanAttributes: true }
        }
      },
      'proso.user':          {
        cwd: '../proso_user',
        src: [
          'static/tpl/*.html',
        ],
        dest: '../proso_user/static/dist/js/templates.js',
        options:    {
          htmlmin:  { collapseWhitespace: true, collapseBooleanAttributes: true }
        }
      }
    },
    uglify: {
      options: {
        banner: '/*! <%= pkg.name %> <%= grunt.template.today("yyyy-mm-dd") %> */\n',
        sourceMap: true
      },
      app: {
        src: [
          'static/js/app.js',
          'static/js/controllers.js',
          'static/js/services.js',
          'static/js/filters.js',
          'static/js/directives.js',
          'static/dist/js/templates.js',
          '../proso_feedback/static/js/app.js',
          '../proso_feedback/static/dist/js/templates.js',
          '../proso_user/static/js/app.js',
          '../proso_user/static/dist/js/templates.js',
        ],
        dest: 'static/dist/js/<%= pkg.name %>.min.js'
      },
      fallbacks: {
        src: [
          'static/lib/js/fallbacks.js',
        ],
        dest: 'static/dist/js/fallbacks.min.js'
      },
      libs: {
        src: [
        /*
          'static/lib/angular-1.2.9/i18n/angular-locale_cs.js',
          'static/lib/js/jquery-1.11.0.js',
          'static/lib/angular-1.2.9/angular.js',
          'static/lib/js/chroma.js',
          'static/lib/js/bootstrap.js',
          'static/lib/angular-1.2.9/angular-route.js',
          'static/lib/angular-1.2.9/angular-cookies.js',
          'static/lib/angular-1.2.9/angular-animate.js',
          'static/lib/js/angulartics.min.js',
          'static/lib/js/angulartics-ga.min.js',
          'static/lib/js/angular-timer.js',
          'static/lib/js/ng-polymer-elements.js',
          'static/lib/angular-material/angular-material.js',
          */
          'static/bower_components/jquery/dist/jquery.js',
          'static/bower_components/angular/angular.js',
          'static/bower_components/chroma-js/chroma.js',
          'static/bower_components/bootstrap/dist/js/bootstrap.js',
          'static/bower_components/angular-route/angular-route.js',
          'static/bower_components/angular-cookies/angular-cookies.js',
          'static/bower_components/angular-animate/angular-animate.js',
          'static/bower_components/angular-sanitize/angular-sanitize.js',
          'static/bower_components/angular-aria/angular-aria.js',
          'static/bower_components/hammerjs/hammer.js',
          'static/bower_components/angulartics/dist/angulartics.min.js',
          'static/bower_components/angulartics/dist/angulartics-ga.min.js',
          'static/bower_components/angular-timer/dist/angular-timer.js',
          'static/bower_components/angular-material/angular-material.js',
          'static/bower_components/angular-bootstrap/ui-bootstrap.js',
          'static/bower_components/angular-bootstrap/ui-bootstrap-tpls.js',
        ],
        dest: 'static/dist/js/libs.min.js'
      }
    },
    jshint: {
      options: {
          "undef": true,
          "unused": true,
          "browser": true,
          "globals": {
              "angular": false
          },
          "maxcomplexity": 5,
          "indent": 2,
          "maxstatements": 12,
          "maxdepth" : 2,
          "maxparams": 11,
          "maxlen": 110
      },
      build: {
        src: 'static/js/',
      }
    },
    watch: {
      options: {
        interrupt: true,
      },
      styles: {
        files: ['static/sass/*.sass'],
        tasks: ['styles'],
      },
      jstpl: {
        files: ['static//jstpl/*.js'],
        tasks: ['string-replace'],
      },
      templates: {
        files: [
          '../proso_feedback/static/tpl/*.html',
          '../proso_user/static/tpl/*.html', 
          'static/tpl/*.html'
        ],
        tasks: ['templates', 'concat:app'],
      },
      jsapp: {
        files: [
          '../proso_feedback/static/js/*.js',
          '../proso_user/static/js/*.js',
          'static/js/*.js'
          ],
        tasks: ['concat:app'],
      },
      jslibs: {
        files: ['static/lib/js/*.js', 'static/lib/angular-1.2.9/*.js'],
        tasks: ['uglify:libs'],
      },
    },
    rename: {
        moveAboveFoldCss: {
            src: 'static/css/above-fold.css',
            dest: 'templates/generated/above-fold.css'
        },
        moveBlueAboveFoldCss: {
            src: 'static/css/blue-above-fold.css',
            dest: 'templates/generated/blue-above-fold.css'
        },
    },
    protractor: {
      options: {
        configFile: "static/test/spec.js", // Default config file
        keepAlive: true, // If false, the grunt process stops when the test fails.
        noColor: false, // If true, protractor will not use colors in its output.
        args: {
          // Arguments passed to the command
        }
      },
      tests: {
        options: {
          args: {} // Target-specific arguments
        }
      },
    },
    vulcanize: {
      default: {
        options: {},
        files: {
          'static/dist/vulcanized.html': [
            'static/bower_components/paper-radio-group/paper-radio-group.html',
            'static/bower_components/paper-radio-group/paper-radio-button.html',
          ]
        },
      },
    },
  });

  // Load plugins.
  grunt.loadNpmTasks('grunt-contrib-uglify');
  grunt.loadNpmTasks('grunt-contrib-jshint');
  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-contrib-sass');
  grunt.loadNpmTasks('grunt-notify');
  grunt.loadNpmTasks('grunt-rename');
  grunt.loadNpmTasks('grunt-newer');
  grunt.loadNpmTasks('grunt-angular-templates');
  grunt.loadNpmTasks('grunt-contrib-concat');
  grunt.loadNpmTasks('grunt-string-replace');
  grunt.loadNpmTasks('grunt-shell');
  grunt.loadNpmTasks('grunt-protractor-runner');
  grunt.loadNpmTasks('grunt-vulcanize');

  // Default task(s).
  grunt.registerTask('styles', ['sass','rename']);
  grunt.registerTask('runserver', ['shell:runserver','watch']);
  grunt.registerTask('templates', ['newer:concat', 'ngtemplates']);
  grunt.registerTask('minifyjs', ['templates', 'uglify']);
  grunt.registerTask('default', ['styles', 'jshint', 'minifyjs']);
  grunt.registerTask('deploy', ['styles', 'minifyjs', 'vulcanize']);
};
