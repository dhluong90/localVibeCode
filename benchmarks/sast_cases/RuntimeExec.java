public class RuntimeExec {
  public void run(String cmd) throws Exception {
    Runtime.getRuntime().exec(cmd);
  }
}
