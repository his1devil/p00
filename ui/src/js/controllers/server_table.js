app.controller('ServerTableCtrl', function($scope, $http) {
    $scope.sqls = [];
    $http.get("api/sql.json").success(function(response) {
        $scope.sqls = response;
    });

    $scope.sort = function(keyname) {
        $scope.sortKey = keyname;
        $scope.reverse = !$scope.reverse;
    }

});
