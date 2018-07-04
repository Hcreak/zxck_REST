function encode () {
    var enusername = hex_md5($("#inputEmail3").val());
    $("#inputEmail3").val(enusername);
    var enpassword = hex_md5($("#inputPassword3").val());
    $("#inputPassword3").val(enpassword);
};