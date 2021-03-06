var gulp = require('gulp');
var sass = require('gulp-sass')(require('sass'));
var watchify = require('watchify');
var browserify = require('browserify');
var source = require('vinyl-source-stream');
var buffer = require('vinyl-buffer');
var sourcemaps = require('gulp-sourcemaps');
var es = require('event-stream');
var minify = require('gulp-minify');
var cleanCSS = require('gulp-clean-css');
var concat = require('gulp-concat');

var config = {
  js: {
    src: [
      './js/main.js',
    ],
    outputDir: './build/',
  },
  sass: {
    src: './sass/**/*.scss',
    dest: './css',
  }
}


gulp.task('sass', () =>
  gulp.src(config.sass.src)
    .pipe(sass({includePaths: config.sass.include}))
    .pipe(sass().on('error', sass.logError))
    .pipe(cleanCSS())
    .pipe(concat('style-min.css'))
    .pipe(gulp.dest(config.sass.dest))
);

var buildJs = (watch, done) => {
    // map each js source file to a stream
    var tasks = config.js.src.map((entry) => {
      var bundler = browserify({
        entries: [entry],
        cache: {},
        packageCache: {},
        debug: true,
        transform: []
      });

      var bundle = () => bundler.bundle()
          .pipe(source(entry))
          .pipe(buffer())
          .pipe(minify({noSource: true}))
          .pipe(gulp.dest(config.js.outputDir));

      if (watch) {
        bundler = watchify(bundler);
        bundler.on('update', bundle);
        bundler.on('log', console.log);
      }

      return bundle();
    });

    // create a merged stream
    merged = es.merge(tasks);

    if (watch) {
      return merged;
    } else {
      return merged.on('end', done);
    }
};

gulp.task('js', (done) => buildJs(false, done));
gulp.task('default', gulp.parallel('sass', 'js'));
