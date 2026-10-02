@rem Gradle wrapper script
@set CLASSPATH=%~dp0gradle\wrapper\gradle-wrapper.jar
@java %JAVA_OPTS% -classpath "%CLASSPATH%" org.gradle.wrapper.GradleWrapperMain %*
