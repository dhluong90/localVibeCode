import java.sql.Connection;
import java.sql.ResultSet;

public class SqlConcat {
  public ResultSet find(Connection c, String id) throws Exception {
    return c.createStatement().executeQuery("SELECT * FROM users WHERE id = '" + id + "'");
  }
}
