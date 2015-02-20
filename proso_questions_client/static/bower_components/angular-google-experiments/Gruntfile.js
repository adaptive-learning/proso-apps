module.exports = function(grunt) {
    grunt.initConfig({
        uglify: {
            options: {
                mangle: false
            },
            googleExperiments: {
                files: {
                    'googleExperiments.min.js': [
                        'src/googleExperimentsModule.js',
                        'src/googleExperimentsProvider.js',
                        'src/googleExperimentsDirective.js'
                    ]
                }
            }
        }
    });
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.registerTask('default', ['uglify']);
};
