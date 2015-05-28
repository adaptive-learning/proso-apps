module.exports = function(grunt) {
    'use strict';

    grunt.initConfig({
        bower_concat: {
            all: {
                dest: 'testapp/static/dist/js/bower-libs.js',
                cssDest: 'testapp/static/dist/css/bower-libs.css',
                mainFiles: {
                    'proso-apps-js': 'proso-apps-services.js',
                },
                exclude: [
                    'angular-bootstrap',
                    'angulartics',
                    'waypoints',
                ]
            }
        },
        watch: {
            'proso-apps': {
                files: 'bower_components/proso-apps-js/*',
                tasks: ['bower_concat']
            }
        }
    });

    grunt.loadNpmTasks('grunt-bower-concat');
    grunt.loadNpmTasks('grunt-contrib-watch');

    grunt.registerTask('default', 'bower_concat');

};
